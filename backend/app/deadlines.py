from datetime import datetime
from fastapi import HTTPException
from app import models


def assert_before_submission_deadline(hackathon: models.Hackathon):
    """Raises 403 if the hackathon's submission deadline has passed.
    This is the server-side enforcement point; the frontend disabling
    edit controls is a UX convenience only and is never trusted alone.
    """
    if hackathon.submission_deadline and datetime.utcnow() > hackathon.submission_deadline:
        raise HTTPException(
            status_code=403,
            detail="Submission deadline has passed for this hackathon; edits are locked.",
        )


def assert_before_registration_deadline(hackathon: models.Hackathon):
    if hackathon.registration_deadline and datetime.utcnow() > hackathon.registration_deadline:
        raise HTTPException(status_code=403, detail="Registration deadline has passed for this hackathon.")
