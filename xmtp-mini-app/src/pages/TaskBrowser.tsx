import { useState, useEffect } from "react";
import { api } from "../services/api";
import { TaskCard } from "../components/TaskCard";
import { CategoryFilter } from "../components/CategoryFilter";
import type { Task } from "../services/types";

export function TaskBrowser() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [category, setCategory] = useState("");

  useEffect(() => {
    loadTasks();
  }, [category]);

  async function loadTasks() {
    setIsLoading(true);
    try {
      const params: Record<string, string> = { status: "published", limit: "20" };
      if (category) params.category = category;
      const data = await api.get<any>("/api/v1/tasks", params);
      const list = Array.isArray(data) ? data : data.tasks ?? [];
      setTasks(list);
    } catch (err) {
      console.error("Failed to load tasks:", err);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="px-4 pt-4 pb-2">
      <h1 className="text-white text-2xl font-bold mb-4">Buscar Tareas</h1>

      <CategoryFilter selected={category} onChange={setCategory} />

      <div className="mt-4 space-y-3">
        {isLoading ? (
          <div className="flex justify-center py-12">
            <div className="w-6 h-6 border-2 border-white/20 border-t-white rounded-full animate-spin" />
          </div>
        ) : tasks.length === 0 ? (
          <p className="text-white/40 text-center py-12">No hay tareas disponibles</p>
        ) : (
          tasks.map((task) => <TaskCard key={task.id} task={task} />)
        )}
      </div>
    </div>
  );
}
