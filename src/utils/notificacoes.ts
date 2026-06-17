// Notificações do navegador (lembretes de revisão). Best-effort e opt-in.

export async function pedirPermissaoNotificacao(): Promise<boolean> {
  if (typeof window === 'undefined' || !('Notification' in window)) return false;
  if (Notification.permission === 'granted') return true;
  if (Notification.permission === 'denied') return false;
  try {
    return (await Notification.requestPermission()) === 'granted';
  } catch {
    return false;
  }
}

export function notificar(titulo: string, corpo: string): void {
  try {
    if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'granted') {
      new Notification(titulo, { body: corpo, icon: '/icon.svg' });
    }
  } catch {
    /* ignore */
  }
}
