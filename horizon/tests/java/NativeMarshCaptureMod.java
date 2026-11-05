package terraforged.qa;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
/** Separate actual-loader reference companion, never part of production. */
public final class NativeMarshCaptureMod implements ModInitializer {
    @Override public void onInitialize() {
        ServerLifecycleEvents.SERVER_STARTED.register(server->{
            try {
                if(!net.minecraft.SharedConstants.getCurrentVersion().name().equals("26.2"))throw new AssertionError("Wrong game version");
                Class.forName("NativeMarshSamplerProbe").getMethod("main",String[].class).invoke(null,(Object)new String[]{System.getProperty("terraforged.qa.inputs"),System.getProperty("terraforged.qa.production"),System.getProperty("terraforged.qa.output")});
                System.out.println("MARSH_FABRIC_SERVER_CAPTURE_OK minecraft=26.2");
            } catch(Throwable error) { error.printStackTrace();System.err.println("MARSH_FABRIC_SERVER_CAPTURE_FAILED"); }
            finally { server.halt(false); }
        });
    }
}
