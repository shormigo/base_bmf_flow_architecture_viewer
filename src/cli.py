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

def _render_svg_with_mmdc(mmd_path: Path, svg_path: Path, width: Optional[int] = None, height: Optional[int] = None, background: Optional[str] = None) -> bool:
    try:
        cmd = ["mmdc", "-i", str(mmd_path), "-o", str(svg_path)]
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

def _render_svg_from_code(code: str, svg_path: Path, width: Optional[int] = None, height: Optional[int] = None, background: Optional[str] = None) -> bool:
    # Write code to a temporary .mmd file and render via mmdc
    with tempfile.NamedTemporaryFile(mode="w", suffix=".mmd", delete=False, encoding="utf-8") as tmp:
        tmp.write(code)
        tmp_path = Path(tmp.name)
    ok = _render_svg_with_mmdc(tmp_path, svg_path, width=width, height=height, background=background)
    try:
        tmp_path.unlink(missing_ok=True)
    except Exception:
        pass
    return ok


@click.command()
@click.argument("object_path", type=click.Path(exists=True, file_okay=False))
@click.option("--out", "out_path", type=click.Path(), default="flow.mmd", help="Output .mmd file path")
@click.option("--variant-detailed", "variant_choice", flag_value="detailed", default=True, help="Generate detailed diagram with operational metadata")
@click.option("--variant-overview", "variant_choice", flag_value="overview", help="Generate overview diagram (clean, minimal)")
@click.option("--variant-both", "variant_choice", flag_value="both", help="Generate both detailed and overview diagrams")
@click.option("--render-png", "render_format", flag_value="png", help="Render PNG output via Mermaid CLI (mmdc)")
@click.option("--render-svg", "render_format", flag_value="svg", help="Render SVG output via Mermaid CLI (mmdc)")
@click.option("--render-both", "render_format", flag_value="both", help="Render both PNG and SVG outputs")
@click.option("--render-scale", type=float, default=2.0, show_default=True, help="PNG scale factor (mmdc -s)")
@click.option("--png-width", type=int, default=None, help="PNG/SVG width in pixels (overrides scale for PNG)")
@click.option("--png-height", type=int, default=None, help="PNG/SVG height in pixels (overrides scale for PNG)")
@click.option("--png-bg", type=str, default=None, help="PNG/SVG background color (e.g. #ffffff, transparent). Defaults based on scheme.")
@click.option("--edge-labels/--no-edge-labels", "edge_labels", default=True, help="Show labels on edges (arrows) indicating task types")
@click.option("--scheme-default", "scheme_choice", flag_value="default", default=True, help="Use default (bright) color scheme")
@click.option("--scheme-dark", "scheme_choice", flag_value="dark", help="Use dark (saturated) color scheme")
@click.option("--scheme-both", "scheme_choice", flag_value="both", help="Generate diagrams with both color schemes")
@click.option("--direction", type=click.Choice(["TD", "LR", "BT"], case_sensitive=False), default=None)
@click.option("--hide-utility/--show-utility", default=True, help="Hide utility tasks like SetEnvironmentVariables for cleaner diagrams")
def main(object_path: str, out_path: str, variant_choice: str, render_format: Optional[str], render_scale: float, png_width: Optional[int], png_height: Optional[int], png_bg: Optional[str], edge_labels: bool, scheme_choice: str, direction: Optional[str], hide_utility: bool):
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
    if variant_choice in ("detailed", "both"):
        variants_to_gen.append(("detailed", True))
    if variant_choice in ("overview", "both"):
        variants_to_gen.append(("overview", False))

    # Determine which schemes to generate
    schemes_to_gen = []
    if scheme_choice == "both":
        schemes_to_gen = ["default", "dark"]
    else:
        schemes_to_gen = [scheme_choice]

    # Generate timestamp for filenames: MMDDYYYY_HHMMSS
    timestamp = datetime.now().strftime("%m%d%Y_%H%M%S")

    for scheme in schemes_to_gen:
        for var_name, show_params in variants_to_gen:
            # Detailed mode: show utility tasks and enhanced details
            # Overview mode: hide utility tasks for cleaner view
            hide_util = not show_params  # detailed=False hides, detailed=True shows
            gen = MermaidGenerator(direction=direction, color_scheme=scheme, hide_utility_tasks=hide_util)
            code = gen.generate(result.graph, title=f"{obj_name} ({var_name})", label_edges=edge_labels, show_params=show_params)

            # Generate filename: {object_name}_{timestamp}_flow_architecture_{scheme}_{variant}
            filename = f"{obj_name}_{timestamp}_flow_architecture_{scheme}_{var_name}.mmd"
            out_dir = Path(out_path).parent if Path(out_path).parent.name else Path(".")
            mmd_path = out_dir / filename
            _write_text(mmd_path, code)
            click.echo(f"Wrote {var_name} Mermaid ({scheme}) to {mmd_path}")

            # Render PNG and/or SVG if requested
            if render_format:
                # Determine background default by scheme if not provided
                bg = png_bg
                if bg is None:
                    bg = "#1e1e1e" if scheme.lower() == "dark" else "#ffffff"
                
                render_png = render_format in ("png", "both")
                render_svg = render_format in ("svg", "both")

                if render_png:
                    code_png = gen.generate(
                        result.graph,
                        title=f"{obj_name} ({var_name})",
                        label_edges=edge_labels,
                        show_params=show_params,
                        png_safe=False,
                    )
                    png_path = mmd_path.with_suffix(".png")
                    if _render_png_from_code(code_png, png_path, scale=render_scale if (png_width is None and png_height is None) else None, width=png_width, height=png_height, background=bg):
                        click.echo(f"Rendered {var_name} PNG ({scheme}) to {png_path}")
                    else:
                        # Fallback: try sanitized version
                        code_png_safe = gen.generate(
                            result.graph,
                            title=f"{obj_name} ({var_name})",
                            label_edges=edge_labels,
                            show_params=show_params,
                            png_safe=True,
                        )
                        if _render_png_from_code(code_png_safe, png_path, scale=render_scale if (png_width is None and png_height is None) else None, width=png_width, height=png_height, background=bg):
                            click.echo(f"Rendered {var_name} PNG ({scheme}, fallback) to {png_path}")
                        else:
                            click.echo(f"{var_name} PNG ({scheme}) rendering skipped due to mmdc error.")
                
                if render_svg:
                    code_svg = gen.generate(
                        result.graph,
                        title=f"{obj_name} ({var_name})",
                        label_edges=edge_labels,
                        show_params=show_params,
                        png_safe=False,
                    )
                    svg_path = mmd_path.with_suffix(".svg")
                    if _render_svg_from_code(code_svg, svg_path, width=png_width, height=png_height, background=bg):
                        click.echo(f"Rendered {var_name} SVG ({scheme}) to {svg_path}")
                    else:
                        # Fallback: try sanitized version
                        code_svg_safe = gen.generate(
                            result.graph,
                            title=f"{obj_name} ({var_name})",
                            label_edges=edge_labels,
                            show_params=show_params,
                            png_safe=True,
                        )
                        if _render_svg_from_code(code_svg_safe, svg_path, width=png_width, height=png_height, background=bg):
                            click.echo(f"Rendered {var_name} SVG ({scheme}, fallback) to {svg_path}")
                        else:
                            click.echo(f"{var_name} SVG ({scheme}) rendering skipped due to mmdc error.")


if __name__ == "__main__":
    main()
