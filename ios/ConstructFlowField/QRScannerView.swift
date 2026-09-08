import SwiftUI
import AVFoundation

/// AVFoundation Camera View Controller for scanning cryptographically signed daily QR codes.
public class QRScannerViewController: UIViewController, AVCaptureMetadataOutputObjectsDelegate {
    public var captureSession: AVCaptureSession?
    public var previewLayer: AVCaptureVideoPreviewLayer?
    public var onCodeScanned: ((String) -> Void)?

    public override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = UIColor.black
        setupCaptureSession()
    }

    private func setupCaptureSession() {
        let session = AVCaptureSession()
        
        guard let videoCaptureDevice = AVCaptureDevice.default(for: .video) else {
            failed(reason: "Camera device unavailable on simulator or device without camera.")
            return
        }

        let videoInput: AVCaptureDeviceInput
        do {
            videoInput = try AVCaptureDeviceInput(device: videoCaptureDevice)
        } catch {
            failed(reason: error.localizedDescription)
            return
        }

        if session.canAddInput(videoInput) {
            session.addInput(videoInput)
        } else {
            failed(reason: "Cannot add video input to capture session.")
            return
        }

        let metadataOutput = AVCaptureMetadataOutput()
        if session.canAddOutput(metadataOutput) {
            session.addOutput(metadataOutput)
            metadataOutput.setMetadataObjectsDelegate(self, queue: DispatchQueue.main)
            metadataOutput.metadataObjectTypes = [.qr]
        } else {
            failed(reason: "Cannot add metadata output to capture session.")
            return
        }

        previewLayer = AVCaptureVideoPreviewLayer(session: session)
        if let previewLayer = previewLayer {
            previewLayer.frame = view.layer.bounds
            previewLayer.videoGravity = .resizeAspectFill
            view.layer.addSublayer(previewLayer)
        }

        self.captureSession = session
        DispatchQueue.global(qos: .userInitiated).async {
            session.startRunning()
        }
    }

    private func failed(reason: String) {
        let label = UILabel()
        label.text = "Camera Scan Active\n(\(reason))"
        label.textColor = .white
        label.textAlignment = .center
        label.numberOfLines = 0
        label.font = UIFont.systemFont(ofSize: 14, weight: .semibold)
        label.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(label)
        
        NSLayoutConstraint.activate([
            label.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            label.centerYAnchor.constraint(equalTo: view.centerYAnchor),
            label.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 20),
            label.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -20)
        ])
    }

    public func metadataOutput(_ output: AVCaptureMetadataOutput, didOutput metadataObjects: [AVMetadataObject], from connection: AVCaptureConnection) {
        if let metadataObject = metadataObjects.first {
            guard let readableObject = metadataObject as? AVMetadataMachineReadableCodeObject else { return }
            guard let stringValue = readableObject.stringValue else { return }
            AudioServicesPlaySystemSound(SystemSoundID(kSystemSoundAudioServicesGSMIncomingCall))
            onCodeScanned?(stringValue)
        }
    }

    public override func viewWillDisappear(_ animated: Bool) {
        super.viewWillDisappear(animated)
        if captureSession?.isRunning == true {
            captureSession?.stopRunning()
        }
    }
}

/// SwiftUI wrapper component for QRScannerViewController.
public struct QRScannerView: UIViewControllerRepresentable {
    public var onCodeScanned: (String) -> Void

    public init(onCodeScanned: @escaping (String) -> Void) {
        self.onCodeScanned = onCodeScanned
    }

    public func makeUIViewController(context: Context) -> QRScannerViewController {
        let vc = QRScannerViewController()
        vc.onCodeScanned = onCodeScanned
        return vc
    }

    public func updateUIViewController(_ uiViewController: QRScannerViewController, context: Context) {}
}
