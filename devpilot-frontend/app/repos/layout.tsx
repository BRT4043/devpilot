import Header from "@/components/Header";

export default function ReposLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-grid flex min-h-full flex-1 flex-col">
      <Header />
      {children}
    </div>
  );
}
