import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from src.graph.builder import GraphBuilder
from src.rendering import MermaidGenerator


def _write_text(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _render_png_with_mmdc(mmd_path: Path, png_path: Path, scale: Optional[float] = None, width: Optional[int] = None, height: Optional[int] = None, background: Optional[str] = None) -> bool:
    try:
        cmd = ["mmdc", "-i", str(mmd_path), "-o", str(png_path)]
        if scale is not None:
            cmd.extend(["-s", str(scale)])
        if width is not None:
            cmd.extend(["-w", str(width)])
        if height is not None:
            cmd.extend(["-H", str(height)])
        if background is not None:
            cmd.extend(["-b", str(background)])
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except FileNotFoundError:
        click.echo("mmdc not found. Install Mermaid CLI: npm i -g @mermaid-js/mermaid-cli", err=True)
        return False
    except subprocess.CalledProcessError as e:
        click.echo(f"mmdc failed: {e.stderr.decode('utf-8', 'ignore')}", err=True)
        return False

def _render_png_from_code(code: str, png_path: Path, scale: Optional[float] = None, width: Optional[int] = None, height: Optional[int] = None, background: Optional[str] = None) -> bool:
    # Write code to a temporary .mmd file and render via mmdc
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False, encoding="utf-8") as tmp:
        tmp.write(code)
        tmp_path = Path(tmp.name)
    ok = _render_png_with_mmdc(tmp_path, png_path, scale=scale, width=width, height=height, background=background)
    try:
        tmp_path.unlink(missing_ok=True)
    except Exception:
        pass
    return ok


@click.command()
@click.argument("object_path", type=click.Path(exists=True, file_okay=False))
@click.option("--out", "out_path", type=click.Path(), default="flow.mmd", help="Output .mmd file path")
@click.option("--variant", type=click.Choice(["detailed", "overview", "both"], case_sensitive=False), default="detailed", help="Diagram variant: overview (clean), detailed (with params), or both")
@click.option("--png/--no-png", default=False, help="Also render PNG via Mermaid CLI (mmdc)")
@click.option("--png-scale", type=float, default=2.0, show_default=True, help="PNG scale factor (mmdc -s)")
@click.option("--png-width", type=int, default=None, help="PNG width in pixels (overrides scale if set)")
@click.option("--png-height", type=int, default=None, help="PNG height in pixels (overrides scale if set)")
@click.option("--png-bg", type=str, default=None, help="PNG background color (e.g. #ffffff, transparent). Defaults based on scheme.")
@click.option("--labels/--no-labels", default=True, help="Include edge labels when possible")
@click.option("--scheme", type=click.Choice(["default", "dark"], case_sensitive=False), default="default", help="Color scheme to use")
@click.option("--direction", type=click.Choice(["TD", "LR", "BT"], case_sensitive=False), default=None)
@click.option("--hide-utility/--show-utility", default=True, help="Hide utility tasks like SetEnvironmentVariables for cleaner diagrams")
def main(object_path: str, out_path: str, variant: str, png: bool, png_scale: float, png_width: Optional[int], png_height: Optional[int], png_bg: Optional[str], labels: bool, scheme: str, direction: Optional[str], hide_utility: bool):
    """Build the flow graph and generate a Mermaid diagram from OBJECT_PATH."""
    builder = GraphBuilder(object_path)
    result = builder.build()
    if not result.success:
        click.echo("Build failed:")
        for err in result.errors:
            click.echo(f" - {err}")
        # Continue to attempt diagram if graph exists
        if result.graph is None:
            raise click.Abort()

    obj_name = result.metadata.get("object_name", "flow")
    variants_to_gen = []
    if variant in ("detailed", "both"):
        variants_to_gen.append(("detailed", True))
    if variant in ("overview", "both"):
        variants_to_gen.append(("overview", False))

    # Generate timestamp for filenames
    timestamp = datetime.now().strftime("%m%d%Y%H%M%S")

    for var_name, show_params in variants_to_gen:
        # Detailed mode: show utility tasks and enhanced details
        # Overview mode: hide utility tasks for cleaner view
        hide_util = not show_params  # detailed=False hides, detailed=True shows
        gen = MermaidGenerator(direction=direction, color_scheme=scheme, hide_utility_tasks=hide_util)
        code = gen.generate(result.graph, title=f"{obj_name} ({var_name})", label_edges=labels, show_params=show_params)

        # Generate filename: {object_name}_flow_architecture_{scheme}_{variant}_{timestamp}
        filename = f"{obj_name}_flow_architecture_{scheme}_{var_name}_{timestamp}.mmd"
        out_dir = Path(out_path).parent if Path(out_path).parent.name else Path(".")
        mmd_path = out_dir / filename
        _write_text(mmd_path, code)
        click.echo(f"Wrote {var_name} Mermaid to {mmd_path}")

        if png:
            # Use same generator for PNG (already has hide_utility setting)
            code_png = gen.generate(
                result.graph,
                title=f"{obj_name} ({var_name})",
                label_edges=labels,
                show_params=show_params,
                png_safe=False,
            )
            png_path = mmd_path.with_suffix(".png")
            # Determine background default by scheme if not provided
            bg = png_bg
            if bg is None:
                bg = "#1e1e1e" if scheme.lower() == "dark" else "#ffffff"
            if _render_png_from_code(code_png, png_path, scale=png_scale if (png_width is None and png_height is None) else None, width=png_width, height=png_height, background=bg):
                click.echo(f"Rendered {var_name} PNG to {png_path}")
            else:
                # Fallback: try sanitized version
                code_png_safe = gen.generate(
                    result.graph,
                    title=f"{obj_name} ({var_name})",
                    label_edges=labels,
                    show_params=show_params,
                    png_safe=True,
                )
                if _render_png_from_code(code_png_safe, png_path, scale=png_scale if (png_width is None and png_height is None) else None, width=png_width, height=png_height, background=bg):
                    click.echo(f"Rendered {var_name} PNG (fallback) to {png_path}")
                else:
                    click.echo(f"{var_name} PNG rendering skipped due to mmdc error.")


if __name__ == "__main__":
    main()
