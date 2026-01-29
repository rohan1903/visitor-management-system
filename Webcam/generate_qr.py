import qrcode



# Replace with your actual IP address

host_url = "https://f70fe7fc7796.ngrok-free.app"  # your PC's IP



img = qrcode.make(host_url)

img.save("visitor_qr.png")

print(f"✅ QR code generated at visitor_qr.png pointing to: {host_url}")