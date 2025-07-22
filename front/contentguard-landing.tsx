import Image from "next/image"
import { Button } from "@/components/ui/button"

export default function Component() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 flex flex-col items-center justify-between p-6 text-white max-w-sm mx-auto">
      {/* Header with Logo */}
      <div className="pt-8 pb-4">
        <div className="flex items-center gap-1 text-xl font-bold">
          <span className="bg-red-500 text-white px-2 py-1 rounded">Dev</span>
          <span className="bg-white text-black px-2 py-1 rounded">aktus</span>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col items-center justify-center text-center space-y-6">
        {/* Title */}
        <div className="space-y-2">
          <h1 className="text-2xl font-bold">
            Meet <span className="text-red-500">ContentGuard</span> !
          </h1>
          <p className="text-gray-300 text-sm leading-relaxed max-w-xs">
            Instantly analyze your content with AI.
            <br />
            Ask ContentGuardian anything
            <br />
            before you publish!
          </p>
        </div>

        {/* Robot Illustration */}
        <div className="py-8">
          <Image
            src="/robot-illustration.png"
            alt="ContentGuard AI Robot"
            width={200}
            height={200}
            className="object-contain"
          />
        </div>
      </div>

      {/* Bottom CTA Section */}
      <div className="w-full space-y-4 pb-8">
        <Button
          className="w-full bg-pink-500 hover:bg-pink-600 text-white font-semibold py-3 rounded-full text-base"
          size="lg"
        >
          Create An Account
        </Button>

        <p className="text-center text-gray-400 text-sm">Already have one</p>
      </div>
    </div>
  )
}
