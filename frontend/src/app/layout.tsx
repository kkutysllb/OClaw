import "@/styles/globals.css";
import "katex/dist/katex.min.css";

import type { Metadata } from "next";
import { type ReactNode } from "react";

import { DesktopProviders } from "@/components/desktop/providers";

export const metadata: Metadata = {
  title: "OClaw",
  icons: {
    icon: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <DesktopProviders>{children}</DesktopProviders>
      </body>
    </html>
  );
}
