import type { Metadata } from "next";
import { IBM_Plex_Mono, Manrope } from "next/font/google";
import { AuthProvider } from "@/lib/auth";
import "@/styles/globals.css";

const manrope = Manrope({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-manrope",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-mono",
  display: "swap",
});

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
    <html lang="en" className={`${manrope.variable} ${plexMono.variable}`}>
      <body>
        {/* Apply the stored theme before paint so a light-mode reload never
            flashes the dark default. Dark is the default (no attribute). */}
        <script
          dangerouslySetInnerHTML={{
            __html:
              "try{if(localStorage.getItem('epsca-theme')==='light'){document.documentElement.setAttribute('data-theme','light')}}catch(e){}",
          }}
        />
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
