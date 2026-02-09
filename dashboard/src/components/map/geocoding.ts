/**
 * Geocoding utilities for LocationPicker
 *
 * Functions for converting addresses to coordinates and vice versa
 * using OpenStreetMap's Nominatim API.
 */

// Geocoding function (using Nominatim - free, no API key needed)
export async function geocodeAddress(
  query: string
): Promise<{ lat: number; lng: number; display_name: string } | null> {
  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
        query
      )}&limit=1`,
      {
        headers: {
          'User-Agent': 'Execution Market Dashboard',
        },
      }
    );

    const data = await response.json();
    if (data.length > 0) {
      return {
        lat: parseFloat(data[0].lat),
        lng: parseFloat(data[0].lon),
        display_name: data[0].display_name,
      };
    }
    return null;
  } catch (error) {
    console.error('Geocoding error:', error);
    return null;
  }
}

// Reverse geocoding function
export async function reverseGeocode(
  lat: number,
  lng: number
): Promise<string | null> {
  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`,
      {
        headers: {
          'User-Agent': 'Execution Market Dashboard',
        },
      }
    );

    const data = await response.json();
    if (data.display_name) {
      // Return a shorter version of the address
      const parts = data.display_name.split(', ');
      return parts.slice(0, 3).join(', ');
    }
    return null;
  } catch (error) {
    console.error('Reverse geocoding error:', error);
    return null;
  }
}
