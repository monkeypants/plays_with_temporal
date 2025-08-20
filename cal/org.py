from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from cal.domain import Schedule


def generate_org_content(
    schedule: Schedule,
    title: str = "Calendar Schedule",
    section_title: str = "Time Blocks",
) -> str:
    """
    Generate org-mode content from a Schedule object using Jinja2 templates.

    Args:
        schedule: The Schedule object containing time blocks
        title: Title for the org-mode document
        section_title: Title for the main section

    Returns:
        String containing org-mode formatted content
    """
    # Get the template directory path
    template_dir = Path(__file__).parent / "templates"

    # Ensure template directory exists
    if not template_dir.exists():
        raise FileNotFoundError(
            f"Template directory not found: {template_dir}"
        )

    # Create Jinja2 environment with autoescape enabled
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["org", "html", "xml"]),
    )
    template = env.get_template("schedule.org.j2")

    # Render the template
    return template.render(
        title=title,
        section_title=section_title,
        time_blocks=schedule.time_blocks,
    )
