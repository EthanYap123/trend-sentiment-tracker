import "./globals.css";

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

export const metadata = {
  title: "Tech Trend Sentiment Tracker",
  description:
    "Automated ETL pipeline and dashboard tracking sentiment across tech and market news from Hacker News, DEV.to and six RSS feeds.",
  icons: { icon: `${basePath}/icon.svg` },
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f6f6f3" },
    { media: "(prefers-color-scheme: dark)", color: "#0d0d0d" },
  ],
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
