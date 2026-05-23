FULL = "full"
STORY_ONLY = "story_only"
TEST_ONLY = "test_only"
AUTOMATION_ONLY = "automation_only"
QA_REVIEW_ONLY = "qa_review_only"

WORKFLOW_MODES = {
    FULL: [
        "intake",
        "requirements",
        "jira_story",
        "test_design",
        "automation_design",
        "dev_handoff",
        "qa_review",
        "finalizer",
    ],
    STORY_ONLY: [
        "intake",
        "requirements",
        "jira_story",
        "qa_review",
        "finalizer",
    ],
    TEST_ONLY: [
        "intake",
        "requirements",
        "test_design",
        "qa_review",
        "finalizer",
    ],
    AUTOMATION_ONLY: [
        "intake",
        "requirements",
        "test_design",
        "automation_design",
        "qa_review",
        "finalizer",
    ],
    QA_REVIEW_ONLY: [
        "intake",
        "qa_review",
        "finalizer",
    ],
}
