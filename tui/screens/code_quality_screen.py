"""
Code Quality Skill Selection Screen
====================================

Allows user to select a code quality skill preset for the agent.
"""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Label, OptionList, Static
from textual.widgets.option_list import Option

from ..events import CodeQualitySkillSelected

# Default presets directory (relative to this file)
PRESETS_DIR = Path(__file__).parent.parent.parent / "agent" / "skills" / "code-quality" / "presets"


class CodeQualityScreen(ModalScreen):
    """Screen for selecting a code quality skill preset."""

    CSS = """
    CodeQualityScreen {
        align: center middle;
    }

    #cq-dialog {
        width: 80;
        height: 24;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #cq-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }

    #cq-content {
        height: 1fr;
    }

    #preset-list {
        height: 100%;
        width: 100%;
    }

    #browse-tree {
        height: 100%;
        width: 100%;
        display: none;
    }

    #cq-buttons {
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    #cq-buttons Button {
        margin: 0 1;
    }

    .selected-info {
        height: 2;
        margin-top: 1;
        color: $text-muted;
    }
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "select", "Select"),
    ]

    def __init__(self, start_dir: Path | None = None):
        super().__init__()
        self._start_dir = start_dir or PRESETS_DIR
        self._selected_file: Path | None = None
        self._browse_mode = False

    def compose(self) -> ComposeResult:
        with Container(id="cq-dialog"):
            yield Label("Select Code Quality Skill", id="cq-title")

            with Vertical(id="cq-content"):
                yield OptionList(id="preset-list")
                yield DirectoryTree(str(self._start_dir.parent), id="browse-tree")

            yield Static("", id="selected-info", classes="selected-info")

            with Horizontal(id="cq-buttons"):
                yield Button("Select", variant="primary", id="btn-select")
                yield Button("Browse...", id="btn-browse")
                yield Button("Skip", id="btn-skip")

    def on_mount(self) -> None:
        """Load presets on mount."""
        self._load_presets()

    def _load_presets(self) -> None:
        """Load available presets from the presets directory."""
        preset_list = self.query_one("#preset-list", OptionList)
        preset_list.clear_options()

        if not PRESETS_DIR.exists():
            return

        presets = sorted(PRESETS_DIR.glob("*.md"))
        for preset in presets:
            label = self._extract_preset_label(preset)
            preset_list.add_option(Option(label, id=str(preset)))

        if presets:
            preset_list.highlighted = 0
            self._selected_file = presets[0]
            self._update_selected_info()

    def _extract_preset_label(self, preset: Path) -> str:
        """Extract a display label from a preset file.

        Attempts to parse YAML frontmatter to find the language field.
        Falls back to the file stem if parsing fails.

        Args:
            preset: Path to the preset markdown file

        Returns:
            Display label for the preset (e.g., "python-ruff (Python)")
        """
        try:
            content = preset.read_text(encoding="utf-8")
            if not content.startswith("---"):
                return preset.stem

            end = content.find("---", 3)
            if end <= 0:
                return preset.stem

            frontmatter = content[3:end]
            for line in frontmatter.split("\n"):
                if line.startswith("language:"):
                    lang = line.split(":", 1)[1].strip()
                    return f"{preset.stem} ({lang})"

            return preset.stem
        except (OSError, ValueError, UnicodeDecodeError):
            return preset.stem

    def _update_selected_info(self) -> None:
        """Update the selected file info display."""
        info = self.query_one("#selected-info", Static)
        if self._selected_file:
            info.update(f"Selected: {self._selected_file.name}")
        else:
            info.update("No skill selected")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle preset selection."""
        if event.option.id:
            self._selected_file = Path(event.option.id)
            self._update_selected_info()

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        """Handle preset highlight (for keyboard navigation)."""
        if event.option.id:
            self._selected_file = Path(event.option.id)
            self._update_selected_info()

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Handle file selection from directory browser."""
        if event.path.suffix == ".md":
            self._selected_file = event.path
            self._update_selected_info()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-select":
            self.post_message(CodeQualitySkillSelected(self._selected_file))
            self.dismiss()
        elif event.button.id == "btn-browse":
            self._toggle_browse_mode()
        elif event.button.id == "btn-skip":
            self.post_message(CodeQualitySkillSelected(None))
            self.dismiss()

    def _toggle_browse_mode(self) -> None:
        """Toggle between preset list and directory browser."""
        self._browse_mode = not self._browse_mode

        preset_list = self.query_one("#preset-list", OptionList)
        browse_tree = self.query_one("#browse-tree", DirectoryTree)
        browse_btn = self.query_one("#btn-browse", Button)

        if self._browse_mode:
            preset_list.display = False
            browse_tree.display = True
            browse_btn.label = "Presets"
        else:
            preset_list.display = True
            browse_tree.display = False
            browse_btn.label = "Browse..."

    def action_cancel(self) -> None:
        """Cancel and return None."""
        self.post_message(CodeQualitySkillSelected(None))
        self.dismiss()

    def action_select(self) -> None:
        """Select current file."""
        self.post_message(CodeQualitySkillSelected(self._selected_file))
        self.dismiss()
