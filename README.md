# BMF Flow Visualizer

Automatically generate Mermaid diagrams and PNG visualizations from BMF flow Python code and YAML configurations.

## Features

- **Automatic Flow Analysis** - AST-based Python parser extracts explicit and implicit dependencies
- **Implicit Dependency Detection** - Automatically discovers task relationships from constructor parameters (input_table, input_paths)
- **YAML Integration** - Parse and enrich with filters, merges, and mappings with heuristic metadata matching
- **Beautiful Diagrams** - Styled Mermaid diagrams with icons, colors, and shapes
- **Multiple Variants** - Generate overview (executive) and detailed (technical) versions
  - **Overview**: Hides utility tasks, clean minimal labels
  - **Detailed**: Shows all tasks with operational metadata (merge rules, filter types, aggregation details)
- **Color Schemes** - Switch between default (bright) and dark themes
- **High-Resolution PNG** - Auto-render diagrams with configurable scale (default 3x) and dimensions
- **Smart Edge Labels** - Task types on edges, detailed metadata for filters/merges/mappings
- **Graph Validation** - Detect cycles, isolated tasks, and disconnected components
- **Timestamped Output** - Filenames include timestamp for version tracking

## Quick Start

### Installation

```bash
# Install Node.js locally (user space)
curl -LO https://nodejs.org/dist/v18.20.4/node-v18.20.4-linux-x64.tar.xz
tar -xf node-v18.20.4-linux-x64.tar.xz

# Add it to your PATH
echo 'export PATH=$HOME/node-v18.20.4-linux-x64/bin:$PATH' >> ~/.bashrc
source ~/.bashrc

# Verify
node -v
npm -v

# Install Mermaid CLI for PNG rendering
npm install --prefix ~/.local @mermaid-js/mermaid-cli

# Add the local bin directory to PATH:
echo 'export PATH=$HOME/.local/node_modules/.bin:$PATH' >> ~/.bashrc
source ~/.bashrc

# Verify
mmdc --version

# Make Puppeteer args persistent (recommended): 
# this disables dependencies on Chromium, which can cuse potential issues
echo 'export PUPPETEER_ARGS="--no-sandbox --disable-setuid-sandbox"' >> ~/.bashrc
source ~/.bashrc

# Clone the repository
cd bmf_flow_visualizer

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

```bash
# Generate Mermaid diagram
python -m src /path/to/object

# Or use the convenience script
./scripts/visualize_flow.sh /path/to/object
```

This creates `flow.mmd` in the current directory.

### Common Options

```bash
# Generate PNG output
python -m src /path/to/object --png

# Specify output file
python -m src /path/to/object --out /tmp/my_flow.mmd

# Add edge labels
python -m src /path/to/object --labels

# Choose color scheme
python -m src /path/to/object --scheme dark

# Generate both overview and detailed versions
python -m src /path/to/object --variant both --labels

# Combine all options
python -m src /path/to/object --variant both --scheme dark --png --labels

# Use this one-liner to generate every variant (overview + detailed) in both color schemes (default + dark) with high-res PNGs:
for scheme in default dark; do python -m src /path/to/object --out /path/to/folder/output.mmd --variant both --png --png-scale 6 --scheme "$scheme" --labels --direction TD; done
```
 
## Detailed Usage

### CLI Reference

```
python -m src OBJECT_PATH [OPTIONS]
```

**Arguments:**
- `OBJECT_PATH` - Path to the BMF object directory (required)

**Options:**
- `--out PATH` - Output file path (default: flow.mmd)
- `--variant CHOICE` - Diagram variant: detailed, overview, or both (default: detailed)
- `--png` - Generate PNG output via mmdc
- `--labels / --no-labels` - Show/hide edge labels (default: no-labels)
- `--scheme CHOICE` - Color scheme: default or dark (default: default)
- `--direction CHOICE` - Graph direction: TD, LR, or BT (default: TD)

### Variant Modes

**Detailed Mode** (default):
- Shows all tasks including SetEnvironmentVariables and utility tasks
- Full task type labels (e.g., "Read Excel")
- Rich operational metadata:
  - Merge tasks: "2 merge rules<br/>Tables: filtered_gxpd_export, parsed_gxpd_sec_table"
  - Filter tasks: "Filter: comparison, is_null<br/>5 rules"
  - Aggregation tasks: "Group by: Country Code, Title, presentation__rim"
  - Mapping tasks: "32 mappings"
- Ideal for technical documentation and debugging

**Overview Mode**:
- Hides utility tasks (SetEnvironmentVariables) with automatic bypass routing
- Clean, minimal labels (e.g., "GxPD Export")
- Icon and task name only
- Ideal for executive presentations and high-level architecture

**Both Mode**:
- Generates both variants with timestamped filenames:
  - `{object_name}_flow_architecture_{scheme}_detailed_{MMDDYYYYHHMMSS}.mmd`
  - `{object_name}_flow_architecture_{scheme}_overview_{MMDDYYYYHHMMSS}.mmd`

### Color Schemes

**Default Scheme** (bright colors):
- Input/Output: Light blue
- Filters: Light orange
- Transformations: Light green
- Mappings: Light yellow

**Dark Scheme** (saturated colors):
- Input/Output: Deep blue
- Filters: Deep orange
- Transformations: Deep green
- Mappings: Deep yellow

### Edge Labels

Edges display the source task's type as the label (e.g., "Filter", "Merge", "Mapping"). Enhanced with YAML metadata when available:
- **Filters:** Shows filter types from YAML (e.g. "comparison", "is_null", "is_unique")
- **Merges:** Shows merge rule count and tables merged ("2 merge rules")
- **Mappings:** Shows mapping count from YAML ("32 mappings")
- **Other tasks:** Task type name from task_definitions.yaml

In detailed mode, node labels include comprehensive operational details extracted from YAML configurations.

## Configuration

Task styling is controlled via [config/task_definitions.yaml](config/task_definitions.yaml):

```yaml
ReadExcel:
  display_name: "Read Excel"
  icon: "📄"
  color: "#E3F2FD"
  shape: "circle"    # Override shape for this task type
  category: "input"
  
Filter:
  display_name: "Filter"
  icon: "🔽"
  color: "#FFE0B2"
  category: "transformation"
```

### Shape Options

- `circle` - Double circle `((()))`
- `rounded` - Rounded rectangle `[]`
- `subroutine` - Subroutine `[[]]`
- `hexagon` - Hexagon `{{}}`
- `rect` - Rectangle

### Category Colors

Configure per-category colors for consistency:

```yaml
color_schemes:
  default:
    input: "#E3F2FD"        # Light blue
    transformation: "#FFE0B2" # Light orange
    aggregation: "#C8E6C9"  # Light green
    # ... 9 categories total
  
  dark:
    input: "#1976D2"        # Deep blue
    transformation: "#F57C00" # Deep orange
    aggregation: "#388E3C"  # Deep green
    # ... 9 categories total
```

## Testing

```bash
# Run all tests
python -m pytest tests/

# Run with verbose output
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/unit/test_mermaid_generator.py -v

# Current status: 95/95 tests passing (100%)
```

### Test Coverage

- **Phase 1 (Foundation):** 30/30 tests ✅
- **Phase 2 (Python Parser):** 15/15 tests ✅
- **Phase 3 (YAML Parser):** 25/25 tests ✅
- **Phase 4 (Graph Construction):** 22/22 tests ✅
- **Phase 5 (Mermaid Generation):** 3/3 tests ✅

**Total:** 95/95 tests passing (100% success rate)

## Validation Features

The tool automatically validates your flow and provides warnings for:

### Disconnected Components
```
WARNING: Found 2 disconnected components (treat edges as undirected):
  - Component 1 (size 23): starts with parsed_gxpd_main_table
  - Component 2 (size 2): starts with lookup_resource
```

### Isolated Tasks
```
WARNING: Isolated tasks found: mapped, created_objects, generated_report
```

### Cycles
```
ERROR: Cycle detected in graph: task_a -> task_b -> task_c -> task_a
```

## Project Structure

```
bmf_flow_visualizer/
├── src/
│   ├── __init__.py
│   ├── __main__.py          # Entry point
│   ├── cli.py               # Click-based CLI
│   ├── discovery/           # File discovery & validation
│   │   └── file_locator.py
│   ├── parsers/             # Python & YAML parsers
│   │   ├── python_parser.py
│   │   └── yaml_parser.py
│   ├── models/              # Data structures
│   │   └── task.py
│   ├── graph/               # Graph construction & validation
│   │   └── builder.py
│   ├── rendering/           # Mermaid generation
│   │   └── mermaid_generator.py
│   ├── config/              # Configuration loader
│   │   └── loader.py
│   └── utils/               # Utilities
│       └── logger.py
├── config/
│   └── task_definitions.yaml  # Task styling config
├── scripts/
│   └── visualize_flow.sh      # Convenience wrapper
├── tests/
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── fixtures/              # Test data
├── requirements.txt
├── setup.py
├── README.md
└── ROADMAP.md
```

## 🔧 Troubleshooting

### PNG rendering fails

Make sure Mermaid CLI is installed:
```bash
mmdc --version
```

### Invalid path error

Ensure the path points to a BMF object directory containing:
- `flows/` folder with `creation_flow.py`
- Optional: `filter/`, `mapping/`, `merging_rules/` folders with YAML files

### No edges in diagram

Check that your Python flow file contains task dependencies:
```python
task_b.set_upstream(task_a)
# or
task_b.depends_on(task_a)
```

### Colors not appearing

Verify `config/task_definitions.yaml` contains color_schemes and your tasks have a category assigned.

## Current Status

**Version:** 1.0.0  
**Status:** MVP Ready
**Tests:** 95/95 passing (100%)  
**Last Updated:** January 8, 2026

All phases complete:
- ✅ Phase 1: Foundation & Setup
- ✅ Phase 2: Python Code Parser
- ✅ Phase 3: YAML Parser & Integration
- ✅ Phase 4: Graph Construction
- ✅ Phase 5: Mermaid Generation
- ✅ Phase 6: CLI & Rendering

## 📚 Additional Documentation

- [ROADMAP.md](./ROADMAP.md) - Detailed development roadmap with phase breakdown
- [config/task_definitions.yaml](./config/task_definitions.yaml) - Task type definitions

## 🤝 Contributing

This is an internal BASE project. For questions or contributions, contact Sebastian Hormigo [sebastian.hormigo@groupinfosys.com].

## 📄 License

Internal Project - BASE Life Science

---

**Created:** January, 2026  
**Maintainer:** Sebastian Hormigo [sebastian.hormigo@groupinfosys.com].
