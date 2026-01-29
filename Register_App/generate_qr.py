import qrcode



# Replace with your actual IP address

host_url = "https://verdie-fictive-margret.ngrok-free.dev"  # your PC's IP



img = qrcode.make(host_url)

img.save("visitor_qr.png")

print(f"✅ QR code generated at visitor_qr.png pointing to: {host_url}")