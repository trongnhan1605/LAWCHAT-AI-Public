import { useEffect } from "react";

import AppRouter from "./router/AppRouter";
import { useAuthStore } from "./store/auth.store";

export default function App() {
  const hydrate = useAuthStore((state) => state.hydrate);

  useEffect(() => {
    void hydrate();
  }, [hydrate]);

  return <AppRouter />;
}
