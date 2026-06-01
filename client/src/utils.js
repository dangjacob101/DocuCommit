/**
 * Converts a document title into a URL-safe slug.
 * e.g. "Acme Services Agreement" -> "acme-services-agreement"
 */
export function slugify(title) {
  return title
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '')   // strip special characters
    .replace(/[\s_]+/g, '-')    // spaces/underscores to hyphens
    .replace(/^-+|-+$/g, '')    // trim leading/trailing hyphens
}

export function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}
