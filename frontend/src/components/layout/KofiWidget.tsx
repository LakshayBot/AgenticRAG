'use client'

import Script from 'next/script'

export function KofiWidget() {
  return (
    <Script
      src="https://storage.ko-fi.com/cdn/scripts/overlay-widget.js"
      strategy="lazyOnload"
      onLoad={() => {
        ;(window as any).kofiWidgetOverlay?.draw('lakshaybot', {
          'type': 'floating-chat',
          'floating-chat.donateButton.text': 'Tip',
          'floating-chat.donateButton.background-color': '#A6293B',
          'floating-chat.donateButton.text-color': '#fff',
        })
      }}
    />
  )
}
