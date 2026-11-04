from pathlib import Path
import urllib.request
import json
import os
import shutil
import subprocess

DOWNLOADS = Path("Downloads")
RELEASES = Path("Releases")

def download(url):
	with urllib.request.urlopen(url) as resp:
		return resp.read()

# super crappy msi format parser just to find required .cab files
def get_msi_cabs(msi):
	index = 0
	while True:
		index = msi.find(b".cab", index+4)
		if index < 0:
			return
		yield msi[index-32:index+4].decode("ascii")

MANIFEST_URL = "https://aka.ms/vs/stable/channel"
print("Checking Visual Studio Manifest...")
chman = json.loads(download(MANIFEST_URL))
vsman_url = chman["channelItems"][0]["payloads"][0]["url"]
license = chman["channelItems"][1]["localizedResources"][0]["license"]
vsman = json.loads(download(vsman_url))
packages = vsman["packages"]

version = ""
payloads = []
for i in range(len(packages)-1, -1, -1):
	if packages[i]["id"].startswith("Win11SDK_10.0."):	
		version = packages[i]["version"]
		payloads = packages[i]["payloads"]
		break

def download_payload(filename):
	for p in payloads:
		if p["fileName"] == "Installers\\" + filename:
			data = download(p["url"])
			with open(DOWNLOADS / filename, "wb") as file:
				file.write(data)
			return data			

if not os.environ.get("GITHUB_ACTIONS"):
	yes = input(f"Do you accept Microsoft Visual Studio license: {license} [Y/N] ? ")
	if yes.upper() not in ["", "YES", "Y"]:
		exit(0)

DOWNLOADS.mkdir(exist_ok=True)
for arch in ["x64", "x86"]:
	MSI_FILENAME = f"Windows App Certification Kit Native Components-{arch}_en-us.msi"
	print(f"Downloading {MSI_FILENAME}...")
	msi = download_payload(MSI_FILENAME)			
	cabs = get_msi_cabs(msi)
	for cab in cabs:
		download_payload(cab)

	print(f"Unpacking {MSI_FILENAME}...")
	ARCHIVES = DOWNLOADS / "Archives" / arch
	shutil.rmtree(ARCHIVES, ignore_errors=True)
	subprocess.run(["msiexec.exe", "/a", DOWNLOADS / MSI_FILENAME, "/quiet", "/qn", f"TARGETDIR={ARCHIVES.resolve()}"])

	print(f"Creating Zip in {RELEASES.resolve()}...")
	shutil.make_archive(RELEASES / f"MakeAppx-{version}-{arch}", "zip", next(ARCHIVES.rglob("makeappx.exe")).parent)

print("Done!")
