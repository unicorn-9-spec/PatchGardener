import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "PatchGardener · Small fixes, room to grow", description: "A local-first repository maintenance assistant. Grounded evidence, small patches, and your approval." };
export default function RootLayout({children}: Readonly<{children: React.ReactNode}>) {
  return <html lang="en"><body>{children}</body></html>;
}
