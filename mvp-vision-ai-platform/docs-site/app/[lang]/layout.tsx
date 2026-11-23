import { Footer, Layout } from 'nextra-theme-docs'
import { Head } from 'nextra/components'
import { getPageMap } from 'nextra/page-map'
import type { PageMapItem } from 'nextra'
import type { FC, ReactNode } from 'react'
import SiteHeader from '../../components/SiteHeader'
import 'nextra-theme-docs/style.css'
import '../globals.css'

const NAV_LINKS = [
  { label: 'Defect', href: '/defect' },
  { label: 'Labeler', href: '/labeler' },
  { label: 'Trainer', href: '/platform' },
  { label: 'Runner', href: '/runner' },
  { label: 'Docs', href: '/docs/ko/guide/overview' },
  { label: 'Download', href: '/downloads' },
  { label: 'Activation', href: '/activation' },
]

export const metadata = {
  title: { absolute: '', template: '%s – DICE Docs' },
  description: 'DICE Vision AI Platform documentation',
  icons: {
    icon: [
      { url: '/docs/favicon.ico', sizes: 'any' },
      { url: '/docs/dice_icon.png', type: 'image/png', sizes: '180x180' },
      { url: '/docs/icon-512.png', type: 'image/png', sizes: '512x512' },
    ],
    shortcut: [{ url: '/docs/dice_icon.png', type: 'image/png', sizes: '180x180' }],
    apple: [{ url: '/docs/dice_icon.png', type: 'image/png', sizes: '180x180' }],
  },
}

type LayoutProps = Readonly<{
  children: ReactNode
  params: Promise<{ lang: string }>
}>

function partnerPageMap(items: PageMapItem[], withinRunner = false): PageMapItem[] {
  const hidden = ['configuration', 'native-api', 'archive']
  return items
    .filter((item) => !withinRunner || !('name' in item) || !hidden.includes(item.name))
    .map((item) => {
      if ('children' in item) {
        return { ...item, children: partnerPageMap(item.children, withinRunner || item.name === 'runner') }
      }
      if (withinRunner && 'data' in item) {
        return { data: Object.fromEntries(Object.entries(item.data).filter(([name]) => !hidden.includes(name))) }
      }
      return item
    })
}

const RootLayout: FC<LayoutProps> = async ({ children, params }) => {
  const { lang } = await params
  const navLinks = NAV_LINKS.map((link) =>
    link.label === 'Docs' ? { ...link, href: '/docs/' + lang + '/guide/overview' } : link,
  )
  const allPages = await getPageMap(`/${lang}`)
  const pageMap = process.env.RUNNER_DOCS_AUDIENCE === 'partner' ? partnerPageMap(allPages) : allPages

  const footer = <Footer>© {new Date().getFullYear()} DICE Vision AI Platform</Footer>

  return (
    <html lang={lang} dir="ltr" suppressHydrationWarning>
      <Head
        color={{ hue: 230, saturation: 71, lightness: { light: 41, dark: 62 } }}
        backgroundColor={{ light: '#f1f5f9', dark: '#0f172a' }}
      />
      <body>
        <SiteHeader navLinks={navLinks} />
        <Layout
          footer={footer}
          pageMap={pageMap}
          editLink={null}
          feedback={{ content: null }}
          search={null}
          nextThemes={{ forcedTheme: 'light' }}
          i18n={[
            { locale: 'ko', name: '한국어' },
            { locale: 'en', name: 'English' },
          ]}
          sidebar={{ defaultMenuCollapseLevel: 1, autoCollapse: true }}
        >
          {children}
        </Layout>
      </body>
    </html>
  )
}

export default RootLayout

