import type {Metadata} from "next";
import {SessionProvider, Shell} from "../components/session";
import "./globals.css";
export const metadata: Metadata = {title:"Soup · Experiment tracker",description:"Durable, project-scoped experiment metrics"};
export default function RootLayout({children}:{children:React.ReactNode}) {
  return <html lang="en"><body><SessionProvider><Shell>{children}</Shell></SessionProvider></body></html>;
}
