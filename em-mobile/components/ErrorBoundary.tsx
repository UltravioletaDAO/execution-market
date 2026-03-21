import React from 'react';
import { View, Text, Pressable } from 'react-native';

interface State { hasError: boolean; error: Error | null; }

export class ErrorBoundary extends React.Component<{children: React.ReactNode}, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    if (__DEV__) console.error('[ErrorBoundary]', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <View className="flex-1 bg-black items-center justify-center p-6">
          <Text className="text-white text-xl font-bold mb-4">Something went wrong</Text>
          <Text className="text-gray-400 text-center mb-6">
            {__DEV__ ? this.state.error?.message : 'An unexpected error occurred.'}
          </Text>
          <Pressable
            onPress={() => this.setState({ hasError: false, error: null })}
            className="bg-violet-600 px-6 py-3 rounded-xl"
          >
            <Text className="text-white font-semibold">Try Again</Text>
          </Pressable>
        </View>
      );
    }
    return this.props.children;
  }
}
