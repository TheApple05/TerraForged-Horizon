import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.lang.reflect.*;
import java.util.*;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import raccoonman.reterraforged.world.worldgen.feature.SwampSurfaceFeature;
import raccoonman.reterraforged.world.worldgen.noise.module.Noise;
import raccoonman.reterraforged.world.worldgen.noise.module.Noises;
/** Packaged graph/material methods and the game's real fixed biome-info noise. */
public final class NativeMarshSamplerProbe {
    static String bits(float f){return String.format(Locale.ROOT,"%08x",Float.floatToRawIntBits(f));}
    static String id(BlockState state){return BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString();}
    public static void main(String[] args)throws Exception {
        Path jar=Path.of(args[1]).toRealPath();
        for(Class<?> type:List.of(SwampSurfaceFeature.class,Noises.class,Noise.class)) {
            Path origin=Path.of(type.getProtectionDomain().getCodeSource().getLocation().toURI()).toRealPath();
            if(!jar.equals(origin))throw new AssertionError("Wrong packaged origin "+type);
            System.err.println("PACKAGED_CLASS_ORIGIN="+type.getName()+"="+origin);
        }
        Field field=SwampSurfaceFeature.class.getDeclaredField("MATERIAL_NOISE");field.setAccessible(true);Noise material=(Noise)field.get(null);
        Method method=SwampSurfaceFeature.class.getDeclaredMethod("getMaterial",int.class,int.class,int.class,int.class,SwampSurfaceFeature.Config.class);method.setAccessible(true);
        var config=new SwampSurfaceFeature.Config(Blocks.CLAY.defaultBlockState(),Blocks.GRAVEL.defaultBlockState(),Blocks.DIRT.defaultBlockState());
        StringBuilder out=new StringBuilder();int count=0;
        for(String line:Files.readAllLines(Path.of(args[0]),StandardCharsets.UTF_8)) {
            String[] f=line.split("\\t");String value;
            if(f[1].equals("select")) {
                float v=Float.intBitsToFloat(Integer.parseUnsignedInt(f[2],16));int y=Integer.parseInt(f[3]),water=Integer.parseInt(f[4]);
                value=id(v>0.6?(v<0.75&&y<water?config.clayMaterial():config.gravelMaterial()):config.dirtMaterial());
            } else {
                int x=Integer.parseInt(f[2]),z=Integer.parseInt(f[3]);
                value=switch(f[1]) {
                    case "noise" -> bits(material.compute(x,z,0));
                    case "info" -> String.format(Locale.ROOT,"%016x",Double.doubleToRawLongBits(Biome.BIOME_INFO_NOISE.getValue(x*0.25D,z*0.25D,false)));
                    case "positive" -> Boolean.toString(Biome.BIOME_INFO_NOISE.getValue(x*0.25D,z*0.25D,false)>0.0D);
                    case "material" -> id((BlockState)method.invoke(null,x,Integer.parseInt(f[4]),z,62,config));
                    default -> throw new IllegalArgumentException(f[1]);
                };
            }
            out.append(f[0]).append('\t').append(value).append('\n');count++;
        }
        Files.writeString(Path.of(args[2]),out,StandardCharsets.UTF_8,StandardOpenOption.CREATE_NEW);
        System.out.println("MARSH_SAMPLER_CAPTURE_OK records="+count+" pid="+ProcessHandle.current().pid());
    }
}
