import { create } from "zustand";
import AsyncStorage from "@react-native-async-storage/async-storage";

interface AuthStore {
  wallet: string | null;
  executorId: string | null;
  userType: "worker" | "publisher" | null;
  setWallet: (wallet: string | null) => void;
  setExecutorId: (id: string | null) => void;
  setUserType: (type: "worker" | "publisher") => void;
  reset: () => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  wallet: null,
  executorId: null,
  userType: null,
  setWallet: (wallet) => {
    set({ wallet });
    if (wallet) AsyncStorage.setItem("em_wallet", wallet);
    else AsyncStorage.removeItem("em_wallet");
  },
  setExecutorId: (executorId) => {
    set({ executorId });
    if (executorId) AsyncStorage.setItem("em_executor_id", executorId);
    else AsyncStorage.removeItem("em_executor_id");
  },
  setUserType: (userType) => {
    set({ userType });
    AsyncStorage.setItem("em_user_type", userType);
  },
  reset: () => {
    set({ wallet: null, executorId: null, userType: null });
    AsyncStorage.multiRemove(["em_wallet", "em_executor_id", "em_user_type"]);
  },
}));
