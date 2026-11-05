use std::{error::Error, fs};
use terraforged_native_core::marsh_sampler::MarshSampler;
fn main() -> Result<(), Box<dyn Error>> {
    let sampler = MarshSampler::new()?;
    for line in fs::read_to_string(std::env::args_os().nth(1).ok_or("input TSV required")?)?.lines()
    {
        let f: Vec<_> = line.split('\t').collect();
        let result = match f[1] {
            "info" | "positive" => continue,
            "noise" => format!(
                "{:08x}",
                sampler.value(f[2].parse()?, f[3].parse()?).to_bits()
            ),
            "material" => sampler
                .material(f[2].parse()?, f[4].parse()?, f[3].parse()?, 62)
                .id()
                .to_string(),
            "select" => MarshSampler::select(
                f32::from_bits(u32::from_str_radix(f[2], 16)?),
                f[3].parse()?,
                f[4].parse()?,
            )
            .id()
            .to_string(),
            _ => return Err("unknown marsh operation".into()),
        };
        println!("{}\t{}", f[0], result);
    }
    Ok(())
}
