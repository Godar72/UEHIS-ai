/**
 * UEHIS Authentication & Redirect Utilities
 */

/**
 * Validates that a redirect URL is strictly a safe relative path within the UEHIS application.
 * Prevents Open Redirect vulnerabilities (e.g. protocol-relative URLs '//evil.com',
 * backslash tricks '/\evil.com', or external protocol schemes 'https://evil.com').
 */
export function isSafeRedirect(url: string | null | undefined): boolean {
  if (!url || typeof url !== 'string') {
    return false;
  }

  // Must begin with a single '/'
  if (!url.startsWith('/') || url.startsWith('//')) {
    return false;
  }

  // Reject backslashes which can be abused for URL normalization bypasses
  if (url.includes('\\')) {
    return false;
  }

  // Reject explicit protocol schemes
  if (url.includes('://')) {
    return false;
  }

  // Reject CRLF or control characters
  if (/[\r\n\t]/.test(url)) {
    return false;
  }

  return true;
}

/**
 * Validates RFC-compliant email address format.
 */
export function isValidEmail(email: string | null | undefined): boolean {
  if (!email || typeof email !== 'string') {
    return false;
  }
  const trimmed = email.trim();
  if (trimmed.length === 0 || trimmed.length > 254) {
    return false;
  }
  const emailRegex = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/;
  return emailRegex.test(trimmed);
}
