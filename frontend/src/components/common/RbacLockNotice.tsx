import React from "react";
import { getFriendlyError } from "../../errors/errorRegistry";
import { MessageBar } from "../ui/MessageBar";

interface RbacLockNoticeProps {
  permission?: string;
}

export function RbacLockNotice({ permission }: RbacLockNoticeProps) {
  const friendly = getFriendlyError("forbidden");

  return (
    <MessageBar
      detail={friendly.nextAction}
      message={friendly.message}
      title={friendly.title}
      tone="error"
    />
  );
}
