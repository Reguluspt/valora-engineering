import React from "react";
import ReactDOM from "react-dom/client";

import { DemoReviewQueuePage } from "./DemoReviewQueuePage";
import "../index.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <DemoReviewQueuePage />
  </React.StrictMode>
);
