import "./globals.css"

export const metadata = {
  title: "ContentGuard - AI Content Analysis",
  description: "Instantly analyze your content with AI. Ask ContentGuardian anything before you publish!",
    generator: 'v0.dev'
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  )
}
