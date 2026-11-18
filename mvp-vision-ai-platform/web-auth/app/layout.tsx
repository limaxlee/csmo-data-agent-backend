import "./globals.css"
import "./ax-theme.css"
import { Providers } from "./providers"
import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "DICE Vision AI Platform",
  description: "데이터 라벨링, 모델 학습, 모니터링, 내보내기를 연결하는 통합 Vision AI 운영 플랫폼",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/favicon.svg", type: "image/svg+xml" },
      { url: "/dice_icon.png", type: "image/png", sizes: "180x180" },
      { url: "/icon-512.png", type: "image/png", sizes: "512x512" },
    ],
    shortcut: [{ url: "/dice_icon.png", type: "image/png", sizes: "180x180" }],
    apple: [{ url: "/dice_icon.png", type: "image/png", sizes: "180x180" }],
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="ko">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
