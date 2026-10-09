import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

export function useRealtime() {
  const queryClient = useQueryClient();

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${protocol}://${window.location.host}/ws?token=${encodeURIComponent(token)}`);

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === "task.updated") {
          queryClient.invalidateQueries({ queryKey: ["tasks"] });
        }
        if (message.type === "notification.created") {
          queryClient.invalidateQueries({ queryKey: ["notifications"] });
        }
      } catch {
        // ignore malformed messages
      }
    };

    const ping = window.setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send("ping");
    }, 30000);

    return () => {
      window.clearInterval(ping);
      ws.close();
    };
  }, [queryClient]);
}
