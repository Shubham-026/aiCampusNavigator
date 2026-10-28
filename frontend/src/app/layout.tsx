import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Campus Navigator | Indoor wayfinding",
  description: "Find a clear route between campus rooms and facilities.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
