import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "EPSCAxplor",
  description: "Query and compare EPSCA collective agreements",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
