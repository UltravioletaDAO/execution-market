export function formatUsdc(amount: number | string): string {
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  return num.toFixed(2);
}

export function formatDeadline(deadline: string): string {
  const d = new Date(deadline);
  const now = new Date();
  const diff = d.getTime() - now.getTime();
  if (diff <= 0) return "Expirado";
  const hours = Math.floor(diff / 3_600_000);
  const mins = Math.floor((diff % 3_600_000) / 60_000);
  if (hours > 24) return `${Math.floor(hours / 24)}d ${hours % 24}h`;
  if (hours > 0) return `${hours}h ${mins}m`;
  return `${mins}m`;
}

export function shortId(id: string): string {
  return id.slice(0, 8);
}

export function truncate(text: string, maxLen: number = 100): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen - 3) + "...";
}
