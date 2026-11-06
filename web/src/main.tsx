import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router";
import { Layout } from "./components/Layout";
import { Demo } from "./pages/Demo";
import { HowItWorks } from "./pages/HowItWorks";
import { Landing } from "./pages/Landing";
import { Rulebook } from "./pages/Rulebook";
import { SubmissionPage } from "./pages/SubmissionPage";
import "./styles.css";

const queryClient = new QueryClient({ defaultOptions: { queries: { refetchOnWindowFocus: false, retry: 1 } } });

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { path: "/", element: <Landing /> },
      { path: "/demo", element: <Demo /> },
      { path: "/s/:id", element: <SubmissionPage /> },
      { path: "/rulebook", element: <Rulebook /> },
      { path: "/how-it-works", element: <HowItWorks /> },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
);
