import { useState } from "react";
import { useXMTP } from "../../context/XMTPContext";
import { ConversationThread } from "./ConversationThread";

interface Props {
  taskId: string;
  taskTitle: string;
  agentAddress: string;
}

export function TaskMessages({ taskId, taskTitle, agentAddress }: Props) {
  const { isConnected, connect, isConnecting } = useXMTP();
  const [showThread, setShowThread] = useState(false);

  if (!isConnected) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center">
        <svg className="h-12 w-12 text-white/20 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
        </svg>
        <p className="text-white/60 text-sm mb-4">Conecta XMTP para enviar mensajes al agente</p>
        <button
          onClick={connect}
          disabled={isConnecting}
          className="px-6 py-2 bg-white text-black text-sm font-medium rounded-lg hover:bg-white/90 disabled:opacity-50"
        >
          {isConnecting ? "Conectando..." : "Conectar XMTP"}
        </button>
      </div>
    );
  }

  return (
    <div className="h-96">
      <ConversationThread
        peerAddress={agentAddress}
        onBack={() => {}}
        contextPrefix={`[Task #${taskId.slice(0, 8)}: ${taskTitle}]`}
      />
    </div>
  );
}
