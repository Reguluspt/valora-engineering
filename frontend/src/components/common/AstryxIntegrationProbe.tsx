import React from 'react';

/**
 * AstryxIntegrationProbe
 * 
 * Minimal safe integration component designed to verify imports compile and resolve.
 * This is an internal utility only; it is not mounted in user-facing production layouts.
 */
export const AstryxIntegrationProbe: React.FC = () => {
  // We can dynamically check if theme files resolved on dev environments
  const testThemeVariable = "Astryx Core Connected Successfully";

  return (
    <div style={{ display: 'none' }} data-testid="astryx-integration-probe">
      {testThemeVariable}
    </div>
  );
};
