import {
  View,
  Text,
  Pressable,
  Animated,
  Dimensions,
  StyleSheet,
} from "react-native";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { router } from "expo-router";

const SCREEN_WIDTH = Dimensions.get("window").width;
const DRAWER_WIDTH = SCREEN_WIDTH * 0.75;
const ANIMATION_DURATION = 300;

interface DrawerMenuProps {
  visible: boolean;
  onClose: () => void;
}

interface MenuItem {
  icon: string;
  labelKey: string;
  route: string;
}

const MENU_ITEMS: MenuItem[] = [
  { icon: "\uD83C\uDFC6", labelKey: "drawer.leaderboard", route: "/leaderboard" },
  { icon: "\uD83E\uDD16", labelKey: "drawer.agents", route: "/agents" },
  { icon: "\u2753", labelKey: "drawer.help", route: "/about" },
  { icon: "\u2699\uFE0F", labelKey: "drawer.settings", route: "/settings" },
];

export function DrawerMenu({ visible, onClose }: DrawerMenuProps) {
  const { t } = useTranslation();
  const slideAnim = useRef(new Animated.Value(-DRAWER_WIDTH)).current;
  const overlayAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (visible) {
      Animated.parallel([
        Animated.timing(slideAnim, {
          toValue: 0,
          duration: ANIMATION_DURATION,
          useNativeDriver: true,
        }),
        Animated.timing(overlayAnim, {
          toValue: 1,
          duration: ANIMATION_DURATION,
          useNativeDriver: true,
        }),
      ]).start();
    } else {
      Animated.parallel([
        Animated.timing(slideAnim, {
          toValue: -DRAWER_WIDTH,
          duration: ANIMATION_DURATION,
          useNativeDriver: true,
        }),
        Animated.timing(overlayAnim, {
          toValue: 0,
          duration: ANIMATION_DURATION,
          useNativeDriver: true,
        }),
      ]).start();
    }
  }, [visible, slideAnim, overlayAnim]);

  const handleNavigate = (route: string) => {
    onClose();
    // Small delay so the drawer closes before navigating
    setTimeout(() => {
      router.push(route as never);
    }, 150);
  };

  if (!visible) {
    return null;
  }

  return (
    <View style={styles.container}>
      {/* Dark overlay */}
      <Animated.View style={[styles.overlay, { opacity: overlayAnim }]}>
        <Pressable style={styles.overlayPressable} onPress={onClose} />
      </Animated.View>

      {/* Drawer panel */}
      <Animated.View
        style={[
          styles.drawer,
          { transform: [{ translateX: slideAnim }] },
        ]}
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Execution Market</Text>
          <Text style={styles.headerSubtitle}>Universal Execution Layer</Text>
        </View>

        {/* Separator */}
        <View style={styles.separator} />

        {/* Menu items */}
        <View style={styles.menuList}>
          {MENU_ITEMS.map((item) => (
            <Pressable
              key={item.route}
              style={({ pressed }) => [
                styles.menuItem,
                pressed && styles.menuItemPressed,
              ]}
              onPress={() => handleNavigate(item.route)}
            >
              <Text style={styles.menuIcon}>{item.icon}</Text>
              <Text style={styles.menuLabel}>{t(item.labelKey)}</Text>
            </Pressable>
          ))}
        </View>

        {/* Footer */}
        <View style={styles.footer}>
          <View style={styles.separator} />
          <Text style={styles.footerText}>v1.0.0</Text>
        </View>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    ...StyleSheet.absoluteFillObject,
    zIndex: 100,
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(0, 0, 0, 0.6)",
  },
  overlayPressable: {
    flex: 1,
  },
  drawer: {
    position: "absolute",
    top: 0,
    left: 0,
    bottom: 0,
    width: DRAWER_WIDTH,
    backgroundColor: "#111111",
    paddingTop: 60,
    justifyContent: "space-between",
  },
  header: {
    paddingHorizontal: 20,
    paddingBottom: 16,
  },
  headerTitle: {
    color: "#ffffff",
    fontSize: 20,
    fontWeight: "700",
  },
  headerSubtitle: {
    color: "#9ca3af",
    fontSize: 13,
    marginTop: 4,
  },
  separator: {
    height: 1,
    backgroundColor: "rgba(255, 255, 255, 0.08)",
    marginHorizontal: 20,
  },
  menuList: {
    flex: 1,
    paddingTop: 12,
  },
  menuItem: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 14,
  },
  menuItemPressed: {
    backgroundColor: "rgba(255, 255, 255, 0.06)",
  },
  menuIcon: {
    fontSize: 20,
    marginRight: 14,
    width: 28,
    textAlign: "center",
  },
  menuLabel: {
    color: "#ffffff",
    fontSize: 16,
    fontWeight: "500",
  },
  footer: {
    paddingBottom: 40,
  },
  footerText: {
    color: "#4b5563",
    fontSize: 12,
    textAlign: "center",
    marginTop: 12,
  },
});
