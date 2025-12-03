"""
Helper script to create a simple icon for the application.
Requires PIL/Pillow.
"""

try:
    from PIL import Image, ImageDraw, ImageFont
    import os
    from pathlib import Path
    
    def create_icon():
        """Create a simple application icon."""
        # Create a 256x256 icon
        size = 256
        img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw a medical cross
        cross_size = 150
        cross_width = 30
        center_x, center_y = size // 2, size // 2
        
        # Vertical bar
        draw.rectangle(
            [center_x - cross_width // 2, center_y - cross_size // 2,
             center_x + cross_width // 2, center_y + cross_size // 2],
            fill=(76, 175, 80, 255)  # Green color
        )
        
        # Horizontal bar
        draw.rectangle(
            [center_x - cross_size // 2, center_y - cross_width // 2,
             center_x + cross_size // 2, center_y + cross_width // 2],
            fill=(76, 175, 80, 255)  # Green color
        )
        
        # Save as ICO file
        icon_path = Path(__file__).parent / "icon.ico"
        img.save(icon_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
        print(f"Icon created: {icon_path}")
    
    if __name__ == "__main__":
        create_icon()
        
except ImportError:
    print("PIL/Pillow not installed. Install with: pip install Pillow")
    print("Or use an online icon generator to create icon.ico")

