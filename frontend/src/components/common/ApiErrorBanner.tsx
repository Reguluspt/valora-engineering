import React from "react";
import { getFriendlyErrorFromUnknown } from "../../errors/errorRegistry";
import { MessageBar } from "../ui/MessageBar";

interface ApiErrorBannerProps {
  message: string;
  onDismiss?: () => void;
}

export function ApiErrorBanner({ message, onDismiss }: ApiErrorBannerProps) {
  const friendly = getFriendlyErrorFromUnknown(message);

  return (
    <MessageBar
      detail={friendly.nextAction}
      message={friendly.message}
      onDismiss={onDismiss}
      title={friendly.title}
      tone="error"
    />
  );
}
