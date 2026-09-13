// Remove the background from a photo with Apple's Vision framework (macOS 14+).
// usage: swift cutout.swift in.jpg out.png   -> RGBA PNG, transparent where no subject
import Foundation
import Vision
import CoreImage

let args = CommandLine.arguments
guard args.count == 3 else { FileHandle.standardError.write("usage: cutout.swift in out.png\n".data(using: .utf8)!); exit(64) }
let input = URL(fileURLWithPath: args[1]), output = URL(fileURLWithPath: args[2])
guard let image = CIImage(contentsOf: input, options: [.applyOrientationProperty: true]) else { FileHandle.standardError.write("cannot read image\n".data(using: .utf8)!); exit(2) }

let request = VNGenerateForegroundInstanceMaskRequest()
let handler = VNImageRequestHandler(ciImage: image)
do { try handler.perform([request]) } catch { FileHandle.standardError.write("vision failed: \(error)\n".data(using: .utf8)!); exit(3) }
guard let result = request.results?.first, !result.allInstances.isEmpty else { FileHandle.standardError.write("no subject found\n".data(using: .utf8)!); exit(4) }

let maskBuffer: CVPixelBuffer
do { maskBuffer = try result.generateScaledMaskForImage(forInstances: result.allInstances, from: handler) }
catch { FileHandle.standardError.write("mask failed: \(error)\n".data(using: .utf8)!); exit(5) }
let mask = CIImage(cvPixelBuffer: maskBuffer)

let blend = CIFilter(name: "CIBlendWithMask")!
blend.setValue(image, forKey: kCIInputImageKey)
blend.setValue(CIImage(color: .clear).cropped(to: image.extent), forKey: kCIInputBackgroundImageKey)
blend.setValue(mask, forKey: kCIInputMaskImageKey)
guard let out = blend.outputImage?.cropped(to: image.extent) else { exit(6) }

let ctx = CIContext()
do { try ctx.writePNGRepresentation(of: out, to: output, format: .RGBA8, colorSpace: CGColorSpace(name: CGColorSpace.sRGB)!) }
catch { FileHandle.standardError.write("write failed: \(error)\n".data(using: .utf8)!); exit(7) }
