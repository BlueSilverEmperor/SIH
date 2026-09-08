$dir = "c:\Users\sridh\Desktop\SIH\screenshots"
if (!(Test-Path $dir)) {
    New-Item -ItemType Directory -Force -Path $dir
}

$routes = @(
    @{ name="dashboard"; url="http://127.0.0.1:5000/" },
    @{ name="analytics"; url="http://127.0.0.1:5000/analytics" },
    @{ name="flowchart"; url="http://127.0.0.1:5000/flowchart" },
    @{ name="suppliers"; url="http://127.0.0.1:5000/suppliers" },
    @{ name="blueprint_3d"; url="http://127.0.0.1:5000/blueprint-3d" },
    @{ name="addons"; url="http://127.0.0.1:5000/addons" }
)

foreach ($item in $routes) {
    $file = "$dir\$($item.name).png"
    Write-Host "Capturing $($item.name) from $($item.url)..."
    Start-Process -FilePath "msedge" -ArgumentList "--headless", "--disable-gpu", "--screenshot=$file", "--window-size=1600,1000", "$($item.url)" -Wait
}

Write-Host "All screenshots captured successfully!"
