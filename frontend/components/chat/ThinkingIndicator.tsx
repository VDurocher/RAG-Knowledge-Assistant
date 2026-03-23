"use client";

import { motion } from "framer-motion";

export function ThinkingIndicator() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="flex items-center gap-3 max-w-3xl"
    >
      {/* Avatar */}
      <div className="w-8 h-8 rounded-full bg-[#16112a] border border-[#2d1f5e] flex items-center justify-center flex-shrink-0">
        <span className="text-[#7c3aed] text-sm">⬡</span>
      </div>

      {/* Dots */}
      <div className="bg-[#0f0d17] border border-[#1a1530] rounded-2xl rounded-tl-sm px-4 py-3">
        <div className="flex items-center gap-1.5">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="w-1.5 h-1.5 rounded-full bg-[#7c3aed]"
              animate={{ y: [0, -5, 0] }}
              transition={{
                duration: 0.7,
                repeat: Infinity,
                delay: i * 0.15,
                ease: "easeInOut",
              }}
            />
          ))}
        </div>
      </div>
    </motion.div>
  );
}
