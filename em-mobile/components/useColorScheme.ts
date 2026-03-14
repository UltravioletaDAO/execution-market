import { useColorScheme as useColorSchemeCore } from 'react-native';

export const useColorScheme = (): 'light' | 'dark' => {
  const coreScheme = useColorSchemeCore();
  if (coreScheme === 'light' || coreScheme === 'dark') return coreScheme;
  return 'light';
};
