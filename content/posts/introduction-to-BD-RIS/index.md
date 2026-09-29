+++
date = '2026-09-29T14:17:35+03:00'
draft = true
title = 'Introduction to BD-RIS'
+++

{{< katex >}}

When we usually think about wireless communication, we think about transmitters, receivers, antennas, signal processing, and perhaps base stations. During this seminar, however, I came across an idea that changes this traditional picture: **what if we could also control the environment through which wireless signals travel?**

This is the basic idea behind **Reconfigurable Intelligent Surfaces (RIS)** and, more recently, **Beyond-Diagonal RIS (BD-RIS)**.

What interested me most about these technologies is not a particular optimization algorithm or mathematical formulation, but the larger idea behind them: turning the wireless environment from something we simply have to deal with into something that can actually participate in communication.

## The Wireless Environment Has Always Been Part of the Problem

A wireless signal rarely travels directly from a transmitter to a receiver without being disturbed. Walls, buildings, furniture, vehicles, and many other objects reflect, absorb, scatter, refract, or diffract electromagnetic waves. As a result, the receiver normally sees several copies of the transmitted signal arriving through different paths.

Traditionally, wireless systems have treated these propagation effects as something largely outside our control. Engineers try to compensate for them by improving the transmitter and receiver using techniques such as multiple antennas, beamforming, coding, equalization, and more sophisticated signal processing. Early work on programmable wireless environments proposed a different philosophy: instead of only adapting the communication system to the environment, why not make the environment itself programmable?

This idea later became closely associated with the concept of the **smart radio environment**, where the propagation environment becomes another controllable part of the wireless system.

That is where RIS enters the picture.

## So, What Is an RIS?

A **Reconfigurable Intelligent Surface** is basically a surface containing many controllable electromagnetic elements.

Instead of behaving like an ordinary wall or reflector, the surface can change the way an incoming radio wave is reflected or otherwise manipulated. By coordinating many elements together, the surface can steer more energy toward a desired receiver, reduce interference in another direction, or create a useful indirect path when the direct path is blocked.

A conventional RIS is typically made from a large number of low-cost, nearly passive elements. Each element can change the phase, and depending on the implementation possibly the amplitude, of the incident wave. When all of these small adjustments work together, the surface performs what is often called **passive beamforming**.

One way I found useful to think about it is this:

> A normal wall reflects radio waves according to its physical properties. An RIS tries to make that reflection programmable.

For example, imagine that a base station cannot directly reach a user because a building blocks the line of sight. If an RIS is placed at a suitable location, the signal can travel from the base station to the RIS and then from the RIS to the user. In this way, the RIS can effectively create an alternative propagation path around the obstacle.

Unlike a conventional active relay, a passive RIS does not normally receive a signal, decode it, amplify it, and retransmit it. Instead, it modifies the electromagnetic wave that reaches the surface. This is one reason RIS has attracted attention as a potentially low-power and relatively simple addition to wireless networks.

## An RIS Does Not Have to Be a Metasurface

One point that became clearer to me during the seminar is that **RIS is a broader concept than metasurface**.

RIS implementations can use metamaterial-based or metasurface structures, but they can also be constructed using arrays of tunable antenna elements and electronic components. A major RIS survey explicitly distinguishes between implementations based on antenna arrays and implementations based on metamaterial surfaces.

This distinction is useful because papers sometimes use terms such as *intelligent reflecting surface*, *programmable metasurface*, and *RIS* almost interchangeably, even though their physical implementations can be quite different.

The common idea is not a particular material. The common idea is **controllable interaction with electromagnetic waves**.

## Why Is Conventional RIS Called “Diagonal”?

This is where the transition toward BD-RIS becomes interesting.

A convenient mathematical way to describe an RIS is through a **scattering matrix**. Very loosely speaking, this matrix describes how electromagnetic waves entering different ports or elements of the surface appear at the output.

In a conventional RIS, the elements are usually controlled independently. Each element has its own tunable impedance and is not electrically connected to the other elements through the reconfigurable network.

Because of this independent structure, the corresponding scattering matrix is **diagonal**.

A simple representation is

\[
\mathbf{\Theta}=
\begin{bmatrix}
\theta_1 & 0 & 0\\
0 & \theta_2 & 0\\
0 & 0 & \theta_3
\end{bmatrix}.
\]

The important point is not the matrix itself. It is what the zeros mean.

Each RIS element primarily controls the signal associated with itself. There is no configurable pathway inside the surface that allows energy received by one element to be deliberately routed through another element.

This makes conventional RIS relatively simple, but it also limits how much control the surface has over the incoming wave.

## Enter Beyond-Diagonal RIS

**Beyond-Diagonal RIS**, or **BD-RIS**, relaxes this restriction.

Instead of treating every RIS element as an isolated unit, BD-RIS introduces **reconfigurable connections between different elements**. Electrically, the surface becomes a more general multi-port network.

The scattering matrix therefore no longer needs to contain values only on its diagonal. Off-diagonal entries can also become meaningful:

\[
\mathbf{\Theta}=
\begin{bmatrix}
\theta_{11} & \theta_{12} & \theta_{13}\\
\theta_{21} & \theta_{22} & \theta_{23}\\
\theta_{31} & \theta_{32} & \theta_{33}
\end{bmatrix}.
\]

Conceptually, this is a major difference.

In BD-RIS, a wave interacting with one element can be affected by configurable connections involving other elements. The 2026 BD-RIS tutorial describes this as engineering configurable coupling across the surface so that energy received by one element can flow through other elements.

This gives the surface additional degrees of freedom for manipulating electromagnetic waves.

That is also why BD-RIS is sometimes informally described as **“RIS 2.0.”**

## Single-Connected, Group-Connected, and Fully-Connected RIS

Another concept that helped me understand BD-RIS was looking at the internal connections as different network architectures.

In a **single-connected RIS**, which corresponds to the conventional RIS, each element operates independently.

In a **group-connected RIS**, the elements are divided into groups. Elements inside each group are interconnected, but different groups remain separated. Mathematically, this produces a **block-diagonal scattering matrix**.

Finally, in a **fully-connected RIS**, all the elements can be connected through the reconfigurable impedance network. This offers the greatest flexibility, although naturally at the cost of additional circuit and control complexity.

I like to think about these architectures using a transportation analogy.

A conventional RIS is like a group of houses where each house has its own private driveway but there are no roads between houses.

A group-connected RIS creates small neighborhoods.

A fully-connected RIS creates a complete internal road network.

The more connections we add, the more possible ways we have to route things through the system. In BD-RIS, what is being “routed” is electromagnetic energy rather than cars.

## Reflection Is Only One Possible Mode

Another thing I initially associated too strongly with RIS was reflection.

A surface does not necessarily have to send the signal back toward the same side from which it arrived. Different RIS designs can operate in **reflective**, **transmissive**, or **hybrid transmitting-and-reflecting** modes.

In the hybrid case, part of the incident energy can be directed toward one side of the surface while another part is directed toward the opposite side.

This opens up much more flexible deployment possibilities.

Instead of thinking of an RIS simply as a “smart mirror,” it is probably better to think of advanced RIS architectures as **programmable electromagnetic interfaces**.

## Why Is BD-RIS Interesting?

The main advantage of BD-RIS is **flexibility**.

Conventional RIS already adds a new degree of control to the wireless environment. BD-RIS goes further by increasing the number of ways in which the surface can manipulate an incident wave.

Research comparing these architectures has shown that group-connected and fully-connected designs can provide stronger beamforming capabilities than conventional single-connected RIS under comparable conditions.

But I think the more important lesson is conceptual rather than numerical.

With conventional RIS, we ask:

**“How should every individual element modify the signal?”**

With BD-RIS, the question becomes closer to:

**“How should the entire surface behave as a programmable electromagnetic network?”**

That is a much broader design space.

## RIS Is Also Interesting for Sensing

RIS technology is not limited to communication.

One example we studied is **Integrated Sensing and Communication (ISAC)**, where the same wireless infrastructure is used both to communicate with users and to sense objects or targets.

If a target or user is hidden behind an obstacle, an RIS can create an additional non-line-of-sight path. This can help communication and can also provide useful sensing paths. Research on BD-RIS-assisted ISAC has investigated exactly this possibility and reports improvements in both communication and radar-related signal quality.

This was one of the applications that made the idea of a programmable environment feel especially powerful to me: the environment is no longer only helping deliver information; it can also help the network **observe the physical world**.

## The Same Idea Can Extend Beyond Terrestrial Networks

BD-RIS has also been investigated for **non-terrestrial networks**, including satellite-related scenarios.

Because BD-RIS architectures can support reflective, transmissive, and hybrid operation, they may eventually be useful on buildings, aerial platforms, or other infrastructure where dynamically shaping wireless propagation could improve coverage or connectivity.

So the underlying idea is quite general. RIS does not necessarily belong to one particular frequency band, network topology, or application.

It is really about adding a programmable electromagnetic layer to the network.

## Of Course, More Flexibility Comes With a Cost

BD-RIS should not be interpreted as simply “RIS but better.”

Connecting the elements introduces additional hardware, control, and modeling complexity. The surface must obey physical constraints such as energy conservation, and practical systems must deal with component losses, imperfect impedance matching, finite-resolution control, frequency-dependent behavior, and coupling between nearby elements.

Recent physics-consistent BD-RIS research emphasizes that effects such as **mutual coupling** between RIS elements cannot always be ignored when accurately modeling real systems.

This leads to what I see as one of the most important themes in RIS research: the communication model, circuit model, and electromagnetic model cannot really be separated forever.

A mathematically elegant surface is not necessarily an easily manufacturable one.

## My Main Takeaway

Before this seminar, I mostly thought about wireless communication as a problem involving a transmitter, a channel, and a receiver.

RIS changes that mental model.

With RIS, the channel is no longer completely passive from the network designer's point of view. We can place programmable structures inside the environment and deliberately change how waves propagate.

BD-RIS pushes this idea further. Instead of controlling many isolated reflecting elements, it treats the surface as a more general interconnected electromagnetic network.

So, for me, the progression looks something like this:

**Traditional wireless:**  
*Adapt the transmitter and receiver to the environment.*

**RIS:**  
*Also modify the environment.*

**BD-RIS:**  
*Turn the surface itself into a more general programmable electromagnetic network.*

That is what I find most interesting about the topic.

RIS is not simply another antenna or another relay. It represents a different way of thinking about the wireless channel: rather than accepting propagation as something nature gives us, future wireless systems may increasingly **engineer the propagation environment itself**.
