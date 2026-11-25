import { createContext } from "react";

export const SidebarCollapseContext = createContext<(() => void) | undefined>(undefined);
