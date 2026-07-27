import {
  Outlet,
  ScrollRestoration,
  createRootRoute,
  Scripts,
} from "@tanstack/react-router";
import * as React from "react";
import styles from "../styles.css?url";

export const Route = createRootRoute({
  component: RootComponent,
});

function RootComponent() {
  return (
    <>
      <Outlet />
      <ScrollRestoration />
      <Scripts />
    </>
  );
}
