import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import "../styles/style.css";
import "../styles/interface.css";
import router from "./router.js";
import { initializeAuth } from "../features/auth/api.js";
document.documentElement.dataset.uiTheme = "slate";
initializeAuth();
createRoot(document.getElementById("app")).render(<RouterProvider router={router} />);
