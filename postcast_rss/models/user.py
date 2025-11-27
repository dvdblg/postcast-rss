from datetime import datetime
from typing import Annotated, Optional

from pydantic import (
    BaseModel,
    BeforeValidator,
    SecretStr,
    field_serializer,
    field_validator,
)

EndDate = Annotated[
    Optional[datetime], BeforeValidator(lambda v: v if v != 0 else None)
]


class IlPostUserSubscription(BaseModel):
    id: int
    billing_period: str
    subscription_status: str
    next_payment: datetime
    start_date: datetime
    end_date: EndDate = None

    @property
    def is_expired(self) -> bool:
        """
        Check if the subscription is expired.
        """
        end_date = self.end_date or self.next_payment
        return (end_date is not None) and (end_date < datetime.now())


class IlPostUserMetadata(BaseModel):
    issubscriber: bool = False
    paying_customer: bool = False
    token: SecretStr
    subscription: IlPostUserSubscription | None = None

    @field_validator("subscription", mode="before")
    @classmethod
    def validate_subscription(cls, value) -> IlPostUserSubscription:
        """
        Validate the subscription data.
        """
        if isinstance(value, str):
            return IlPostUserSubscription.model_validate_json(value)
        return value

    @field_serializer("token", when_used="json")
    def dump_secret(self, v):
        return v.get_secret_value()


class IlPostUserProfile(BaseModel):
    meta: IlPostUserMetadata


class IlPostUser(BaseModel):
    id: int
    token: SecretStr
    subscription: bool
    profile: IlPostUserProfile
