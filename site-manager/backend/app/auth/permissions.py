from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from ..users.model import User
from .main import get_current_active_user


class PermissionChecker:
    def __init__(
        self, action: str, resource_type: str, path_param_name: str | None = None
    ):
        self.action = action
        self.resource_type = resource_type
        self.path_param_name = path_param_name

    def __call__(
        self, request: Request, user: Annotated[User, Depends(get_current_active_user)]
    ):
        user_perms = user.permissions.split(" ")

        # --- SCENARIO A: Collection Endpoint (No specific path param) ---
        if not self.path_param_name:
            # Must possess a wildcard to access the full collection
            wildcard_match = f"{self.action}:{self.resource_type}:*"
            global_wildcard = f"*:{self.resource_type}:*"

            if wildcard_match in user_perms or global_wildcard in user_perms:
                return True

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: You do not have global '{self.action}' access to all '{self.resource_type}' resources.",
            )

        # --- SCENARIO B: Instance Endpoint (Has path param) ---
        resource_id = request.path_params.get(self.path_param_name)
        if resource_id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Configuration error: '{self.path_param_name}' missing from route path.",
            )

        res_id_str = str(resource_id)

        exact_match = f"{self.action}:{self.resource_type}:{res_id_str}"
        action_wildcard = f"*:{self.resource_type}:{res_id_str}"
        id_wildcard = f"{self.action}:{self.resource_type}:*"
        full_wildcard = f"*:{self.resource_type}:*"

        has_permission = any(
            perm in user_perms
            for perm in (exact_match, action_wildcard, id_wildcard, full_wildcard)
        )

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Missing '{self.action}' on '{self.resource_type}:{res_id_str}'",
            )

        return True
