/**
 * GPS Permission Hint — platform-specific instructions when geolocation fails.
 *
 * Detects the user's browser/OS combo and returns an i18n key
 * with actionable steps to fix location permission issues.
 */

export type GpsPlatform =
  | 'ios_safari'
  | 'ios_chrome'
  | 'ios_other'
  | 'android_chrome'
  | 'android_samsung'
  | 'android_other'
  | 'brave'
  | 'firefox'
  | 'desktop'

const ua = typeof navigator !== 'undefined' ? navigator.userAgent : ''

export function detectGpsPlatform(): GpsPlatform {
  const isBrave =
    (navigator as Navigator & { brave?: unknown }).brave ||
    /Brave/i.test(ua)
  if (isBrave) return 'brave'

  const isIOS = /iPad|iPhone|iPod/.test(ua) || (/Macintosh/i.test(ua) && 'ontouchend' in document)
  if (isIOS) {
    if (/CriOS/i.test(ua)) return 'ios_chrome'
    if (/Safari/i.test(ua) && !/CriOS|FxiOS|OPiOS|EdgiOS/i.test(ua)) return 'ios_safari'
    return 'ios_other'
  }

  const isAndroid = /Android/i.test(ua)
  if (isAndroid) {
    if (/SamsungBrowser/i.test(ua)) return 'android_samsung'
    if (/Chrome/i.test(ua)) return 'android_chrome'
    return 'android_other'
  }

  if (/Firefox/i.test(ua)) return 'firefox'

  return 'desktop'
}

/**
 * Returns the i18n key for the platform-specific permission hint.
 * Each key maps to a translated string with step-by-step instructions.
 */
export function getPermissionHintKey(platform: GpsPlatform): string {
  switch (platform) {
    case 'ios_safari':
      return 'gps.hint.iosSafari'
    case 'ios_chrome':
      return 'gps.hint.iosChrome'
    case 'ios_other':
      return 'gps.hint.iosOther'
    case 'android_chrome':
      return 'gps.hint.androidChrome'
    case 'android_samsung':
      return 'gps.hint.androidSamsung'
    case 'android_other':
      return 'gps.hint.androidOther'
    case 'brave':
      return 'gps.hint.brave'
    case 'firefox':
      return 'gps.hint.firefox'
    case 'desktop':
    default:
      return 'gps.hint.desktop'
  }
}
