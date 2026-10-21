import type { Metadata } from "next";
import { PythonLab } from "@/features/python-strategy/components/python-lab";

export const metadata: Metadata = { title: "Python 전략 실험실" };

export default function PythonStrategiesPage() {
  return <PythonLab />;
}
