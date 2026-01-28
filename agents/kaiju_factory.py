"""
KaijuFactory - Kawaii Kaiju Coloring Book Asset Generation Pipeline

This module provides the KaijuBookGenerator class for programmatic generation
of structured coloring book projects for the "Kawaii Kaiju" series.

Architecture: Integrates with the Orchestration Layer (Python/Next.js/Supabase)
"""

import json
import os
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

# Mock Supabase interface - replace with actual import when available
# from app.core.db import SupabaseManager


@dataclass
class PageAsset:
    """Represents a single coloring book page."""
    page_number: int
    landmark_name: str
    image_prompt: str
    caption: str
    is_fallback: bool = False  # True if this was a generic fallback


@dataclass
class BookManifest:
    """Complete manifest for a coloring book."""
    book_title: str
    city: str
    marketing_copy: str
    pages: List[Dict[str, Any]]
    generated_at: str
    total_pages: int
    fallback_count: int
    cref_placeholder: str
    sref_placeholder: str


class LandmarkDatabase:
    """
    The Brain: Curated database of high-recognition landmarks and cultural
    scenarios for major world cities.

    Each entry is a specific, recognizable entity - not generic concepts.
    """

    # Kaiju-friendly actions for variety in prompts
    KAIJU_ACTIONS = [
        "happily waving",
        "taking a selfie",
        "eating a snack",
        "doing a cute pose",
        "holding an ice cream cone",
        "wearing a tiny hat",
        "carrying a shopping bag",
        "reading a map",
        "riding a bicycle",
        "flying a kite",
        "sitting on a bench",
        "dancing joyfully",
        "playing with bubbles",
        "holding balloons",
        "giving a thumbs up",
        "doing a peace sign",
        "hugging a giant pretzel",
        "carrying a camera",
        "wearing sunglasses",
        "holding a flower",
    ]

    # Curated landmarks by city - 30+ per city for reliability
    LANDMARKS = {
        "Tokyo": [
            "Tokyo Tower observation deck",
            "Senso-ji Temple in Asakusa",
            "Shibuya Crossing intersection",
            "Tokyo Skytree",
            "Meiji Shrine torii gate",
            "Harajuku Takeshita Street",
            "Akihabara Electric Town",
            "Tsukiji Outer Market",
            "Ueno Park cherry blossoms",
            "Imperial Palace East Gardens",
            "Odaiba Rainbow Bridge",
            "Shinjuku Godzilla Head",
            "Nakamise Shopping Street",
            "Tokyo Station red brick building",
            "Yoyogi Park fountain",
            "Ginza district at night",
            "Roppongi Hills Mori Tower",
            "Kabukicho entertainment district",
            "Sumida River cruise",
            "teamLab Borderless museum",
            "Yanaka historic district",
            "Gotokuji Temple lucky cats",
            "Kappabashi Kitchen Town",
            "Tokyo Dome",
            "Ameya-Yokocho market",
            "Zojoji Temple with Tokyo Tower",
            "Nezu Shrine azalea garden",
            "Inokashira Park swan boats",
            "Aoyama Cemetery cherry trees",
            "Tokyo Metropolitan Building observation",
            "Omotesando Hills",
            "Sunshine City aquarium",
            "Hama-rikyu Gardens tea house",
        ],
        "Paris": [
            "Eiffel Tower",
            "The Louvre Pyramid",
            "Notre-Dame Cathedral",
            "Arc de Triomphe",
            "Sacré-Cœur Basilica",
            "Champs-Élysées boulevard",
            "Moulin Rouge windmill",
            "Palace of Versailles gardens",
            "Musée d'Orsay clock",
            "Pont Alexandre III bridge",
            "Luxembourg Gardens fountain",
            "Place de la Concorde obelisk",
            "Montmartre artists' square",
            "Seine River cruise boat",
            "Tuileries Garden carousel",
            "Palais Royal columns",
            "Saint-Germain-des-Prés café",
            "Le Marais historic district",
            "Canal Saint-Martin locks",
            "Père Lachaise Cemetery",
            "Opéra Garnier grand staircase",
            "Pont des Arts love locks bridge",
            "Shakespeare and Company bookshop",
            "Galeries Lafayette dome",
            "Place des Vosges arcade",
            "Conciergerie towers",
            "Panthéon dome",
            "Jardin des Plantes greenhouse",
            "Sainte-Chapelle stained glass",
            "Musée Rodin garden",
            "Parc des Buttes-Chaumont temple",
            "La Défense Grande Arche",
            "Bois de Boulogne lake",
        ],
        "New York": [
            "Statue of Liberty",
            "Empire State Building observation deck",
            "Times Square billboards",
            "Central Park Bethesda Fountain",
            "Brooklyn Bridge walkway",
            "One World Trade Center",
            "Grand Central Terminal main hall",
            "Rockefeller Center ice rink",
            "The Met Museum steps",
            "DUMBO cobblestone streets",
            "High Line elevated park",
            "Flatiron Building",
            "Wall Street Charging Bull",
            "Radio City Music Hall",
            "Chrysler Building spire",
            "The Vessel at Hudson Yards",
            "Washington Square Arch",
            "Coney Island boardwalk",
            "St. Patrick's Cathedral",
            "Chelsea Market interior",
            "NYPL Main Reading Room",
            "Top of the Rock observation",
            "Little Italy restaurant row",
            "Chinatown lantern streets",
            "Broadway theater district",
            "The Oculus interior",
            "Bow Bridge Central Park",
            "Museum Mile on Fifth Avenue",
            "The Edge observation deck",
            "Stone Street historic district",
            "The Cloisters gardens",
            "Prospect Park Boathouse",
            "Yankee Stadium",
        ],
        "Austin": [
            "Texas State Capitol building",
            "Congress Avenue Bridge bat colony",
            "Barton Springs Pool",
            "South Congress Avenue murals",
            "6th Street entertainment district",
            "Lady Bird Lake kayaking",
            "Mount Bonnell overlook",
            "Zilker Park Botanical Garden",
            "The Driskill Hotel lobby",
            "Rainey Street bungalow bars",
            "Cathedral of Junk art installation",
            "Graffiti Park at Castle Hill",
            "Blanton Museum of Art",
            "The Domain shopping district",
            "Mueller Lake Park",
            "Umlauf Sculpture Garden",
            "Elisabet Ney Museum",
            "Treaty Oak ancient tree",
            "Mayfield Park peacocks",
            "McKinney Falls waterfall",
            "Hamilton Pool Preserve",
            "Austin City Limits Live venue",
            "Bullock Texas State History Museum",
            "360 Bridge overlook",
            "Deep Eddy Pool",
            "Stubb's BBQ amphitheater",
            "Texas Memorial Stadium",
            "The Contemporary Austin",
            "Jo's Coffee 'I Love You So Much' mural",
            "Long Center for Performing Arts",
            "Texas Governor's Mansion",
            "Moonlight Towers",
            "Austin Motel neon sign",
        ],
        # Extensible: Add more cities as needed
        "London": [
            "Big Ben and Parliament",
            "Tower Bridge",
            "Buckingham Palace gates",
            "The London Eye",
            "Tower of London ravens",
            "Westminster Abbey",
            "St. Paul's Cathedral dome",
            "Trafalgar Square lions",
            "Piccadilly Circus billboards",
            "British Museum reading room",
            "Camden Market stalls",
            "Covent Garden performers",
            "Hyde Park Serpentine",
            "Notting Hill colorful houses",
            "Abbey Road crossing",
            "Borough Market food stalls",
            "The Shard observation deck",
            "Greenwich Observatory",
            "Millennium Bridge",
            "Harrods department store",
            "Natural History Museum entrance",
            "Kew Gardens glasshouse",
            "Shakespeare's Globe Theatre",
            "Platform 9¾ at King's Cross",
            "Royal Albert Hall",
            "Regent's Park roses",
            "Victoria and Albert Museum",
            "Sky Garden indoor garden",
            "Neal's Yard colorful courtyard",
            "Primrose Hill viewpoint",
            "Thames River cruise",
            "Churchill War Rooms",
            "Leadenhall Market arcade",
        ],
        "San Francisco": [
            "Golden Gate Bridge",
            "Alcatraz Island cellhouse",
            "Fisherman's Wharf sea lions",
            "Cable Car on Powell Street",
            "Lombard Street curves",
            "Painted Ladies Victorian houses",
            "Chinatown Dragon Gate",
            "Coit Tower murals",
            "Palace of Fine Arts rotunda",
            "Pier 39 carousel",
            "Ferry Building marketplace",
            "Ghirardelli Square",
            "Union Square heart statue",
            "Transamerica Pyramid",
            "Twin Peaks viewpoint",
            "Haight-Ashbury murals",
            "Mission Dolores Park",
            "Japanese Tea Garden",
            "de Young Museum tower",
            "Baker Beach with bridge view",
            "Cliff House ocean view",
            "Castro Theatre marquee",
            "Salesforce Park rooftop",
            "Exploratorium exhibits",
            "Cable Car Museum",
            "Alamo Square panorama",
            "North Beach cafes",
            "The Embarcadero waterfront",
            "Sutro Baths ruins",
            "California Academy of Sciences",
            "Muir Woods redwoods",
            "Treasure Island skyline view",
            "SFMOMA staircase",
        ],
    }

    # Generic fallback activities when specific landmarks run out
    GENERIC_ACTIVITIES = [
        "visiting a charming local café",
        "exploring a colorful street market",
        "riding the city bus",
        "watching street performers",
        "feeding pigeons in the plaza",
        "enjoying local street food",
        "window shopping downtown",
        "visiting a neighborhood park",
        "taking a city walking tour",
        "admiring local architecture",
        "trying local ice cream",
        "browsing a vintage bookshop",
        "attending a local festival",
        "visiting a flower market",
        "enjoying a rooftop view",
    ]

    @classmethod
    def get_landmarks(cls, city: str, count: int = 30) -> tuple[List[str], int]:
        """
        Retrieve landmarks for a city.

        Args:
            city: The city name
            count: Number of landmarks needed (default 30)

        Returns:
            Tuple of (landmarks list, fallback_count)
        """
        landmarks = cls.LANDMARKS.get(city, [])

        if len(landmarks) >= count:
            # Shuffle and return exactly count landmarks
            selected = random.sample(landmarks, count)
            return selected, 0

        # Need fallbacks
        fallback_count = count - len(landmarks)
        fallbacks = [
            f"{activity} in {city}"
            for activity in random.sample(
                cls.GENERIC_ACTIVITIES,
                min(fallback_count, len(cls.GENERIC_ACTIVITIES))
            )
        ]

        # Fill remaining with more generic activities if needed
        while len(fallbacks) < fallback_count:
            fallbacks.append(f"having an adventure in {city}")

        return landmarks + fallbacks, fallback_count

    @classmethod
    def get_random_action(cls) -> str:
        """Get a random Kaiju action for prompt variety."""
        return random.choice(cls.KAIJU_ACTIONS)


class PromptEngine:
    """
    The Moat: Strict image generation prompt engineering for consistent
    Kawaii Kaiju coloring book pages.
    """

    # Base template - optimized for coloring book line art
    BASE_TEMPLATE = (
        "Vector line art, black and white coloring book page, clean thick lines, "
        "no shading, white background. A cute, round, friendly Kaiju monster "
        "{action} at {landmark}."
    )

    # Midjourney/DALL-E style parameters
    STYLE_SUFFIX = " Kawaii style, chibi proportions, simple shapes, child-friendly."

    # Placeholder for character/style references
    CREF_PLACEHOLDER = "--cref [YOUR_CHARACTER_REFERENCE_URL]"
    SREF_PLACEHOLDER = "--sref [YOUR_STYLE_REFERENCE_URL]"

    @classmethod
    def generate_prompt(
        cls,
        landmark: str,
        action: Optional[str] = None,
        include_refs: bool = True
    ) -> str:
        """
        Generate a strict image generation prompt.

        Args:
            landmark: The specific landmark or location
            action: Optional Kaiju action (random if not provided)
            include_refs: Whether to include --cref and --sref placeholders

        Returns:
            Fully constructed prompt string
        """
        if action is None:
            action = LandmarkDatabase.get_random_action()

        prompt = cls.BASE_TEMPLATE.format(action=action, landmark=landmark)
        prompt += cls.STYLE_SUFFIX

        if include_refs:
            prompt += f" {cls.CREF_PLACEHOLDER} {cls.SREF_PLACEHOLDER}"

        return prompt

    @classmethod
    def generate_caption(cls, landmark: str, city: str) -> str:
        """Generate a fun caption for the coloring book page."""
        captions = [
            f"Kaiju discovers the wonders of {landmark}!",
            f"Our friendly Kaiju visits {landmark} in {city}!",
            f"A kawaii adventure at {landmark}!",
            f"Kaiju makes new friends at {landmark}!",
            f"Coloring fun at {landmark}!",
            f"Kaiju's favorite spot: {landmark}!",
            f"What a cute day at {landmark}!",
            f"Kaiju says hello from {landmark}!",
        ]
        return random.choice(captions)


class MarketingCopyGenerator:
    """Generates SEO-optimized marketing copy for Shopify listings."""

    TEMPLATES = [
        (
            "Explore {city} with the cutest Kaiju ever! This {pages}-page coloring book "
            "features adorable kawaii monsters visiting famous landmarks like {landmark1}, "
            "{landmark2}, and more. Perfect for kids ages 4-10. Great for travel prep, "
            "geography learning, and creative fun!"
        ),
        (
            "Take your little artist on a {city} adventure! Our kawaii Kaiju friend "
            "visits {pages} iconic locations including {landmark1} and {landmark2}. "
            "Thick, clean lines perfect for crayons, markers, or colored pencils. "
            "Educational and entertaining for all ages!"
        ),
        (
            "Discover {city} through coloring! Join our adorable Kaiju monster at "
            "{landmark1}, {landmark2}, and {num_more} more famous spots. {pages} pages "
            "of child-friendly illustrations with easy-to-color thick outlines. "
            "The perfect gift for young explorers!"
        ),
    ]

    @classmethod
    def generate(cls, city: str, landmarks: List[str], page_count: int = 30) -> str:
        """Generate ~50 word SEO marketing copy."""
        template = random.choice(cls.TEMPLATES)

        # Select featured landmarks
        featured = random.sample(landmarks[:10], min(2, len(landmarks)))

        copy = template.format(
            city=city,
            pages=page_count,
            landmark1=featured[0] if featured else city,
            landmark2=featured[1] if len(featured) > 1 else "local attractions",
            num_more=page_count - 2,
        )

        return copy


class SupabaseInterface:
    """
    Mock Supabase interface for asset management.
    Replace with actual SupabaseManager integration when available.
    """

    def __init__(self):
        self.connected = False
        self._mock_storage: List[Dict] = []
        self._try_connect()

    def _try_connect(self):
        """Attempt to connect to Supabase."""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if url and key:
            try:
                # Actual connection would go here:
                # from app.core.db import SupabaseManager
                # self.client = SupabaseManager()
                self.connected = True
                print("✅ Supabase connection available")
            except Exception as e:
                print(f"⚠️ Supabase connection failed: {e}")
                self.connected = False
        else:
            print("⚠️ Supabase credentials not found, using local storage only")
            self.connected = False

    def save_manifest(self, manifest: Dict, city: str) -> bool:
        """Save manifest to database (mock implementation)."""
        self._mock_storage.append({
            "city": city,
            "manifest": manifest,
            "created_at": datetime.now().isoformat()
        })
        return True

    def get_manifests(self) -> List[Dict]:
        """Retrieve all stored manifests."""
        return self._mock_storage


class KaijuBookGenerator:
    """
    Main orchestrator for Kawaii Kaiju coloring book generation.

    Accepts a list of cities and generates complete book manifests
    including landmarks, image prompts, and marketing copy.

    Example:
        generator = KaijuBookGenerator()
        results = generator.generate_books(["Tokyo", "Paris", "New York", "Austin"])
    """

    def __init__(
        self,
        output_dir: Optional[str] = None,
        pages_per_book: int = 30,
        include_style_refs: bool = True
    ):
        """
        Initialize the KaijuBookGenerator.

        Args:
            output_dir: Directory for JSON output files (default: ./output)
            pages_per_book: Number of pages per coloring book (default: 30)
            include_style_refs: Include --cref/--sref placeholders in prompts
        """
        self.output_dir = Path(output_dir or Path(__file__).parent / "output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.pages_per_book = pages_per_book
        self.include_style_refs = include_style_refs

        # Initialize database interface
        self.db = SupabaseInterface()

        # Track generation statistics
        self.stats = {
            "books_generated": 0,
            "total_pages": 0,
            "total_fallbacks": 0,
            "cities_processed": [],
        }

        print(f"🦖 KaijuFactory initialized")
        print(f"   Output directory: {self.output_dir}")
        print(f"   Pages per book: {self.pages_per_book}")

    def _generate_book_title(self, city: str) -> str:
        """Generate the book title."""
        return f"Kawaii Kaiju in {city}"

    def _create_page(
        self,
        page_num: int,
        landmark: str,
        city: str,
        is_fallback: bool = False
    ) -> PageAsset:
        """Create a single page asset."""
        prompt = PromptEngine.generate_prompt(
            landmark=landmark,
            include_refs=self.include_style_refs
        )
        caption = PromptEngine.generate_caption(landmark, city)

        return PageAsset(
            page_number=page_num,
            landmark_name=landmark,
            image_prompt=prompt,
            caption=caption,
            is_fallback=is_fallback
        )

    def generate_book(self, city: str) -> BookManifest:
        """
        Generate a complete coloring book manifest for a city.

        Args:
            city: The city name

        Returns:
            BookManifest with all pages and metadata
        """
        print(f"\n📚 Generating book for: {city}")

        # Get landmarks with fallback handling
        landmarks, fallback_count = LandmarkDatabase.get_landmarks(
            city,
            self.pages_per_book
        )

        if fallback_count > 0:
            print(f"   ⚠️ Using {fallback_count} fallback activities (not enough landmarks)")

        # Generate pages
        pages: List[PageAsset] = []
        for i, landmark in enumerate(landmarks, start=1):
            is_fallback = i > (self.pages_per_book - fallback_count)
            page = self._create_page(i, landmark, city, is_fallback)
            pages.append(page)

        # Generate marketing copy
        marketing_copy = MarketingCopyGenerator.generate(
            city,
            landmarks,
            self.pages_per_book
        )

        # Create manifest
        manifest = BookManifest(
            book_title=self._generate_book_title(city),
            city=city,
            marketing_copy=marketing_copy,
            pages=[asdict(p) for p in pages],
            generated_at=datetime.now().isoformat(),
            total_pages=len(pages),
            fallback_count=fallback_count,
            cref_placeholder=PromptEngine.CREF_PLACEHOLDER,
            sref_placeholder=PromptEngine.SREF_PLACEHOLDER,
        )

        print(f"   ✅ Generated {len(pages)} pages")

        return manifest

    def save_manifest(self, manifest: BookManifest) -> Path:
        """
        Save manifest to JSON file.

        Args:
            manifest: The book manifest to save

        Returns:
            Path to the saved file
        """
        # Sanitize city name for filename
        city_slug = manifest.city.lower().replace(" ", "_").replace("'", "")
        filename = f"manifest_{city_slug}.json"
        filepath = self.output_dir / filename

        # Convert to dict and save
        manifest_dict = asdict(manifest)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(manifest_dict, f, indent=2, ensure_ascii=False)

        # Also save to database
        self.db.save_manifest(manifest_dict, manifest.city)

        print(f"   💾 Saved: {filepath}")

        return filepath

    def generate_books(self, cities: List[str]) -> Dict[str, Any]:
        """
        Generate coloring books for multiple cities.

        Args:
            cities: List of city names

        Returns:
            Dictionary with generation results and statistics
        """
        print(f"\n🦖 KaijuFactory: Starting batch generation")
        print(f"   Cities: {', '.join(cities)}")
        print("=" * 50)

        results = {
            "success": [],
            "failed": [],
            "manifests": {},
            "files": [],
        }

        for city in cities:
            try:
                # Generate book
                manifest = self.generate_book(city)

                # Save to file
                filepath = self.save_manifest(manifest)

                # Track results
                results["success"].append(city)
                results["manifests"][city] = asdict(manifest)
                results["files"].append(str(filepath))

                # Update stats
                self.stats["books_generated"] += 1
                self.stats["total_pages"] += manifest.total_pages
                self.stats["total_fallbacks"] += manifest.fallback_count
                self.stats["cities_processed"].append(city)

            except Exception as e:
                print(f"   ❌ Failed to generate book for {city}: {e}")
                results["failed"].append({"city": city, "error": str(e)})

        # Summary
        print("\n" + "=" * 50)
        print("🎉 Generation Complete!")
        print(f"   Books generated: {self.stats['books_generated']}")
        print(f"   Total pages: {self.stats['total_pages']}")
        print(f"   Fallback pages: {self.stats['total_fallbacks']}")

        if results["failed"]:
            print(f"   ⚠️ Failed: {len(results['failed'])} cities")

        results["stats"] = self.stats
        return results


def main():
    """
    Main execution: Generate Kawaii Kaiju coloring books for target cities.
    """
    # Target cities for initial generation
    cities = ["Tokyo", "Paris", "New York", "Austin"]

    # Initialize generator
    generator = KaijuBookGenerator(
        pages_per_book=30,
        include_style_refs=True
    )

    # Generate all books
    results = generator.generate_books(cities)

    # Output summary
    print("\n📁 Generated Files:")
    for filepath in results["files"]:
        print(f"   - {filepath}")

    return results


if __name__ == "__main__":
    main()
