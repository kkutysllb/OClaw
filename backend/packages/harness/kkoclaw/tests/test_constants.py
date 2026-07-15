"""Constants module exposes the shared runtime protocol constants."""
from kkoclaw import constants


def test_default_skills_container_path():
    assert constants.DEFAULT_SKILLS_CONTAINER_PATH == "/mnt/skills"
